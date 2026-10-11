"""Gated DeltaNet (arXiv 2412.06464), the linear-attention mixer used 3:1 with
softmax attention in Qwen3-Next / Kimi Linear style hybrids.

Uses the flash-linear-attention (``fla``) Triton kernels when installed and on
CUDA; otherwise falls back to an exact pure-PyTorch chunked implementation
(WY representation) that is slower but numerically equivalent.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig
from .layers import rms_norm, zero_init

try:  # pragma: no cover - optional dependency
    from fla.ops.gated_delta_rule import chunk_gated_delta_rule as _fla_chunk
    from fla.ops.gated_delta_rule import fused_recurrent_gated_delta_rule as _fla_recurrent
except Exception:
    _fla_chunk = _fla_recurrent = None


# ----------------------------------------------------------------------------
# Reference kernels. Layout: q, k [B, T, H, K]; v [B, T, H, V]; g, beta [B, T, H]
# g is the log-space decay (<= 0); q and k are expected to be L2-normalised.
# ----------------------------------------------------------------------------


def recurrent_gated_delta_rule(q, k, v, g, beta, scale, initial_state=None):
    B, T, H, K = q.shape
    V = v.shape[-1]
    S = (torch.zeros(B, H, K, V, device=q.device, dtype=torch.float32)
         if initial_state is None else initial_state.float())
    q, k, v, g, beta = (t.float() for t in (q, k, v, g, beta))
    out = []
    for t in range(T):
        S = S * g[:, t].exp()[..., None, None]
        kt = k[:, t]
        v_new = (v[:, t] - torch.einsum("bhk,bhkv->bhv", kt, S)) * beta[:, t, :, None]
        S = S + torch.einsum("bhk,bhv->bhkv", kt, v_new)
        out.append(torch.einsum("bhk,bhkv->bhv", q[:, t] * scale, S))
    return torch.stack(out, dim=1), S


def chunk_gated_delta_rule(q, k, v, g, beta, scale, initial_state=None, chunk_size=64):
    B, T, H, K = q.shape
    V = v.shape[-1]
    C = chunk_size
    q, k, v = (t.transpose(1, 2).float() for t in (q, k, v))  # [B, H, T, D]
    g, beta = g.transpose(1, 2).float(), beta.transpose(1, 2).float()  # [B, H, T]
    pad = (-T) % C
    if pad:
        q, k, v = (F.pad(t, (0, 0, 0, pad)) for t in (q, k, v))
        g, beta = F.pad(g, (0, pad)), F.pad(beta, (0, pad))
    N = q.size(2) // C
    q = q * scale
    k_beta, v_beta = k * beta[..., None], v * beta[..., None]
    q, k, k_beta, v_beta = (t.view(B, H, N, C, -1) for t in (q, k, k_beta, v_beta))
    g = g.view(B, H, N, C).cumsum(-1)

    lower = torch.tril(torch.ones(C, C, dtype=torch.bool, device=q.device))
    decay = (g[..., :, None] - g[..., None, :]).masked_fill(~lower, float("-inf")).exp()
    strict = torch.tril(torch.ones(C, C, dtype=torch.bool, device=q.device), diagonal=-1)
    A = ((k_beta @ k.transpose(-1, -2)) * decay).masked_fill(~strict, 0.0)
    eye = torch.eye(C, device=q.device, dtype=q.dtype)
    Tm = torch.linalg.solve_triangular(A + eye, eye.expand_as(A), upper=False, unitriangular=True)
    u = Tm @ v_beta
    w = Tm @ (k_beta * g.exp()[..., None])

    S = (torch.zeros(B, H, K, V, device=q.device, dtype=torch.float32)
         if initial_state is None else initial_state.float())
    out = []
    for n in range(N):
        qn, kn, gn = q[:, :, n], k[:, :, n], g[:, :, n]
        attn = (qn @ kn.transpose(-1, -2)) * decay[:, :, n]
        v_new = u[:, :, n] - w[:, :, n] @ S
        out.append((qn * gn.exp()[..., None]) @ S + attn @ v_new)
        g_last = gn[..., -1]
        S = S * g_last.exp()[..., None, None] + \
            (kn * (g_last[..., None] - gn).exp()[..., None]).transpose(-1, -2) @ v_new
    o = torch.cat(out, dim=2)[:, :, :T]
    return o.transpose(1, 2), S


# ----------------------------------------------------------------------------
# Layer
# ----------------------------------------------------------------------------


class DeltaCache:
    def __init__(self, B, H, K, V, conv_dim, conv_k, device, dtype):
        self.state = torch.zeros(B, H, K, V, device=device, dtype=torch.float32)
        self.conv = torch.zeros(B, conv_k - 1, conv_dim, device=device, dtype=dtype)

    def copy_from(self, other: "DeltaCache", pos: int, T: int):
        self.state.copy_(other.state)
        self.conv.copy_(other.conv)


class GatedDeltaNet(nn.Module):
    def __init__(self, cfg: ModelConfig, conv_size: int = 4):
        super().__init__()
        d = cfg.d_model
        self.H, self.K = cfg.n_head, cfg.head_dim
        self.V = cfg.head_dim
        self.conv_k = conv_size
        self.qkv_dim = self.H * (2 * self.K + self.V)
        self.qkv = nn.Linear(d, self.qkv_dim, bias=False)
        self.conv_w = nn.Parameter(torch.randn(self.qkv_dim, 1, conv_size) / math.sqrt(conv_size))
        self.ab = nn.Linear(d, 2 * self.H, bias=False)  # decay-rate input a, write-strength b
        self.g_proj = nn.Linear(d, self.H * self.V, bias=False)
        self.o = zero_init(nn.Linear(self.H * self.V, d, bias=False))
        A = torch.empty(self.H).uniform_(0.01, 16)  # Qwen3.8 / Qwen4-Exp init
        self.A_log = nn.Parameter(A.log())
        dt = torch.exp(torch.rand(self.H) * (math.log(0.1) - math.log(1e-3)) + math.log(1e-3))
        self.dt_bias = nn.Parameter(dt + torch.log(-torch.expm1(-dt)))  # softplus^-1(dt)

    def _conv(self, x, cache):
        # Causal depthwise conv over time; x: [B, T, C]
        B, T, C = x.shape
        prev = cache.conv if cache is not None else x.new_zeros(B, self.conv_k - 1, C)
        xp = torch.cat([prev.to(x.dtype), x], dim=1)
        if cache is not None:
            cache.conv = xp[:, -(self.conv_k - 1):].detach().clone()
        y = F.conv1d(xp.transpose(1, 2), self.conv_w.to(x.dtype), groups=C)
        return F.silu(y.transpose(1, 2))

    def forward(self, x, cache=None):
        B, T, _ = x.shape
        H, K, V = self.H, self.K, self.V
        if cache is not None and not isinstance(cache, DeltaCache):
            raise TypeError("expected DeltaCache")
        qkv = self._conv(self.qkv(x), cache)
        q, k, v = qkv.split([H * K, H * K, H * V], dim=-1)
        q = F.normalize(q.view(B, T, H, K).float(), dim=-1).to(x.dtype)
        k = F.normalize(k.view(B, T, H, K).float(), dim=-1).to(x.dtype)
        v = v.view(B, T, H, V)
        a, b = self.ab(x).float().chunk(2, dim=-1)
        beta = torch.sigmoid(b)
        g = -self.A_log.float().exp() * F.softplus(a + self.dt_bias.float())
        init = cache.state if cache is not None else None
        scale = K ** -0.5
        if _fla_chunk is not None and x.is_cuda:  # pragma: no cover - GPU path
            fn = _fla_recurrent if T <= 64 and cache is not None else _fla_chunk
            o, S = fn(q, k, v, g, beta.to(x.dtype), scale=scale, initial_state=init,
                      output_final_state=cache is not None)
        elif T <= 16:
            o, S = recurrent_gated_delta_rule(q, k, v, g, beta, scale, init)
        else:
            o, S = chunk_gated_delta_rule(q, k, v, g, beta, scale, init)
        if cache is not None:
            cache.state = S.float()
        o = rms_norm(o.to(x.dtype)) * F.silu(self.g_proj(x).view(B, T, H, V))
        return self.o(o.reshape(B, T, H * V))
