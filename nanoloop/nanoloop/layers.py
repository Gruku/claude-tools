"""Building blocks: norms, partial RoPE, gated attention, ReLU^2 MLP, caches."""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig

try:  # FlashAttention-2 gives native sliding windows; optional.
    from flash_attn import flash_attn_func as _flash_attn_func
except Exception:  # pragma: no cover - depends on the user's machine
    _flash_attn_func = None


def rms_norm(x: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """Parameter-free RMSNorm (modded-nanogpt / nanochat convention)."""
    return F.rms_norm(x, (x.size(-1),), eps=eps)


def zero_init(linear: nn.Linear) -> nn.Linear:
    """Mark a projection to be zero-initialised by the model's init pass."""
    linear._zero_init = True
    return linear


# ----------------------------------------------------------------------------
# Inference caches
# ----------------------------------------------------------------------------


class KVCache:
    """Full-length K/V buffer for one attention layer (one recurrence slot)."""

    def __init__(self, B, n_kv, T_max, head_dim, device, dtype):
        self.k = torch.zeros(B, n_kv, T_max, head_dim, device=device, dtype=dtype)
        self.v = torch.zeros_like(self.k)

    def update(self, k, v, pos):
        T = k.size(2)
        self.k[:, :, pos:pos + T] = k
        self.v[:, :, pos:pos + T] = v
        return self.k[:, :, :pos + T], self.v[:, :, :pos + T]

    def copy_from(self, other: "KVCache", pos: int, T: int):
        self.k[:, :, pos:pos + T] = other.k[:, :, pos:pos + T]
        self.v[:, :, pos:pos + T] = other.v[:, :, pos:pos + T]


class ModelCache:
    """Holds every layer cache for incremental decoding.

    Core (recurrent) layers get one cache per *slot*; iteration i of the loop
    uses slot ``i % n_slots``. A token that exits the loop early has its final
    K/V (or recurrent state) copied into the slots it never reached, so later
    tokens always read "the latest computed state" of earlier tokens — the
    training-free cache-sharing scheme from Huginn (arXiv 2502.05171).
    """

    def __init__(self, batch_size, max_len, n_slots, device, dtype):
        self.B, self.T_max, self.n_slots = batch_size, max_len, n_slots
        self.device, self.dtype = device, dtype
        self.pos = 0
        self.layers: dict = {}
        self.smear_prev = None  # last (normed) embedding, for the smear gate

    def get(self, key, factory):
        if key not in self.layers:
            self.layers[key] = factory()
        return self.layers[key]


# ----------------------------------------------------------------------------
# Rotary embeddings (partial)
# ----------------------------------------------------------------------------


class Rotary(nn.Module):
    """RoPE on the first ``rope_frac`` of each head's dims; the rest stay
    position-free "content" channels (arXiv 2410.06205, modded-nanogpt)."""

    def __init__(self, head_dim: int, frac: float, base: float, max_len: int):
        super().__init__()
        rd = int(head_dim * frac) // 2 * 2
        self.rd = rd
        inv = base ** (-torch.arange(0, rd, 2, dtype=torch.float32) / max(rd, 1))
        f = torch.outer(torch.arange(max_len, dtype=torch.float32), inv)
        self.register_buffer("cos", f.cos(), persistent=False)
        self.register_buffer("sin", f.sin(), persistent=False)

    def forward(self, x: torch.Tensor, pos0: int) -> torch.Tensor:
        # x: [B, T, H, D]
        if self.rd == 0:
            return x
        T = x.size(1)
        assert pos0 + T <= self.cos.size(0), "sequence longer than max_seq_len"
        cos = self.cos[pos0:pos0 + T][None, :, None, :]
        sin = self.sin[pos0:pos0 + T][None, :, None, :]
        xr, xp = x[..., :self.rd].float(), x[..., self.rd:]
        x1, x2 = xr.chunk(2, dim=-1)
        y = torch.cat([x1 * cos + x2 * sin, x2 * cos - x1 * sin], dim=-1)
        return torch.cat([y.type_as(x), xp], dim=-1)


# ----------------------------------------------------------------------------
# Attention
# ----------------------------------------------------------------------------


def causal_mask(Tq: int, Tk: int, pos0: int, window: int | None, device) -> torch.Tensor:
    qpos = torch.arange(Tq, device=device)[:, None] + pos0
    kpos = torch.arange(Tk, device=device)[None, :]
    m = kpos <= qpos
    if window is not None:
        m = m & (kpos > qpos - window)
    return m


class Attention(nn.Module):
    """QK-normed, partially-rotary, gated softmax attention.

    Stack (in order): fused QKV -> RMS QK-norm -> partial RoPE -> value
    embedding + value residual mixing -> SDPA -> gated XSA (subtract the
    component along the token's own value) -> sigmoid output gate (Qwen gated
    attention, arXiv 2505.06708) -> zero-init output projection.
    """

    def __init__(self, cfg: ModelConfig, window: int | None, use_ve: bool, is_first: bool):
        super().__init__()
        self.H, self.Hkv, self.hd = cfg.n_head, cfg.n_kv_head, cfg.head_dim
        self.scale = cfg.attn_scale
        self.window = window
        d = cfg.d_model
        self.qkv = nn.Linear(d, (self.H + 2 * self.Hkv) * self.hd, bias=False)
        self.o = zero_init(nn.Linear(self.H * self.hd, d, bias=False))
        self.gate_mode = cfg.attn_gate
        if cfg.attn_gate == "elementwise":
            self.gate = zero_init(nn.Linear(d, self.H * self.hd, bias=False))
        elif cfg.attn_gate == "headwise":
            self.gate = zero_init(nn.Linear(d, self.H, bias=False))
        else:
            self.gate = None
        self.xsa_alpha = nn.Parameter(torch.zeros(self.H)) if cfg.xsa else None
        self.ve_lambda = nn.Parameter(torch.full((self.Hkv,), 0.5)) if use_ve else None
        self.vres = (nn.Parameter(torch.tensor([0.5, 0.5]))
                     if cfg.value_residual and not is_first else None)

    def _attend(self, q, k, v, pos0):
        # q: [B, H, Tq, D], k/v: [B, Hkv, Tk, D]
        Tq, Tk = q.size(2), k.size(2)
        gqa = self.H != self.Hkv
        if (self.window is not None and _flash_attn_func is not None and q.is_cuda
                and pos0 == 0 and Tq == Tk and q.dtype in (torch.bfloat16, torch.float16)):
            y = _flash_attn_func(q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2),
                                 softmax_scale=self.scale, causal=True,
                                 window_size=(self.window - 1, 0))
            return y.transpose(1, 2)
        if self.window is None and pos0 == 0 and Tq == Tk:
            return F.scaled_dot_product_attention(q, k, v, is_causal=True, scale=self.scale,
                                                  enable_gqa=gqa)
        if self.window is None and Tq == 1:
            return F.scaled_dot_product_attention(q, k, v, scale=self.scale, enable_gqa=gqa)
        mask = causal_mask(Tq, Tk, pos0, self.window, q.device)
        return F.scaled_dot_product_attention(q, k, v, attn_mask=mask, scale=self.scale,
                                              enable_gqa=gqa)

    def forward(self, x, rope: Rotary, pos0: int, v_first=None, ve=None, cache=None):
        B, T, _ = x.shape
        qkv = self.qkv(x).view(B, T, self.H + 2 * self.Hkv, self.hd)
        q, k, v = qkv.split([self.H, self.Hkv, self.Hkv], dim=2)
        q, k = rope(rms_norm(q), pos0), rope(rms_norm(k), pos0)
        if ve is not None:
            v = v + self.ve_lambda.view(1, 1, -1, 1).to(v.dtype) * ve.view(B, T, self.Hkv, self.hd)
        v_out = v
        if self.vres is not None and v_first is not None:
            lam = self.vres.to(v.dtype)
            v = lam[0] * v + lam[1] * v_first
        q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
        if cache is not None:
            k_all, v_all = cache.update(k, v, pos0)
            k_all, v_all = k_all.to(q.dtype), v_all.to(q.dtype)
        else:
            k_all, v_all = k, v
        y = self._attend(q, k_all, v_all, pos0)  # [B, H, T, D]
        if self.xsa_alpha is not None:
            vs = v.repeat_interleave(self.H // self.Hkv, dim=1) if self.H != self.Hkv else v
            coef = (y * vs).sum(-1, keepdim=True) / (vs.pow(2).sum(-1, keepdim=True) + 1e-6)
            y = y - torch.tanh(self.xsa_alpha).view(1, -1, 1, 1).to(y.dtype) * coef * vs
        y = y.transpose(1, 2)  # [B, T, H, D]
        if self.gate is not None:
            g = torch.sigmoid(self.gate(x)).view(B, T, self.H, -1)
            y = y * g
        return self.o(y.reshape(B, T, self.H * self.hd)), v_out


class MLP(nn.Module):
    """ReLU^2 MLP (beat SwiGLU in both modded-nanogpt and nanochat ablations)."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        hidden = int(cfg.mlp_ratio * cfg.d_model)
        self.fc = nn.Linear(cfg.d_model, hidden, bias=False)
        self.proj = zero_init(nn.Linear(hidden, cfg.d_model, bias=False))

    def forward(self, x):
        return self.proj(F.relu(self.fc(x)).square())


class Block(nn.Module):
    """Transformer block. ``sandwich=True`` adds post-sublayer norms (Huginn's
    SandwichBlock), which keeps the looped state bounded across iterations."""

    def __init__(self, cfg: ModelConfig, kind: str, sandwich: bool, use_ve: bool, is_first: bool):
        super().__init__()
        self.kind = kind
        self.sandwich = sandwich
        if kind == "D":
            from .deltanet import GatedDeltaNet
            self.mixer = GatedDeltaNet(cfg)
        else:
            window = cfg.local_window if kind == "L" else None
            self.mixer = Attention(cfg, window, use_ve, is_first)
        self.mlp = MLP(cfg)

    def forward(self, x, rope, pos0, v_first=None, ve=None, cache=None):
        if self.kind == "D":
            h, v = self.mixer(rms_norm(x), cache=cache), None
        else:
            h, v = self.mixer(rms_norm(x), rope, pos0, v_first=v_first, ve=ve, cache=cache)
        x = x + h
        if self.sandwich:
            x = rms_norm(x)
        x = x + self.mlp(rms_norm(x))
        if self.sandwich:
            x = rms_norm(x)
        return x, v


def init_linear_(module: nn.Module):
    """Uniform init with std 0.5/sqrt(fan_in) (modded-nanogpt), or zeros if marked."""
    for m in module.modules():
        if isinstance(m, nn.Linear):
            if getattr(m, "_zero_init", False):
                nn.init.zeros_(m.weight)
            else:
                bound = math.sqrt(3) * 0.5 / math.sqrt(m.in_features)
                nn.init.uniform_(m.weight, -bound, bound)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
