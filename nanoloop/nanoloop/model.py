"""NanoLoop: a recurrent-depth (looped) transformer LM.

    tokens -> embed (+smear) -> PRELUDE (P blocks) -> e = norm(prelude out)
           -> s_0 ~ N(0, sigma^2)
           -> repeat r times:  s = CORE(adapter([s ; e]))    # weight-shared
           -> CODA (C blocks, U-net skips from prelude) -> norm -> softcapped head

Training samples r per step from a log-normal Poisson (mean r_bar) and back-
propagates only through the last k loops (truncated BPTT, Huginn arXiv
2502.05171); e is re-injected every loop and normalised (Parcae arXiv
2604.12946) so the loop is a stable dynamical system. At inference r is a dial:
more loops = more latent compute, optionally with per-token adaptive exit.
"""

from __future__ import annotations

import math
import random

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from .config import ModelConfig
from .deltanet import DeltaCache
from .layers import Block, KVCache, ModelCache, Rotary, init_linear_, rms_norm, zero_init


class NanoLoop(nn.Module):
    def __init__(self, cfg: ModelConfig, seed: int = 0):
        super().__init__()
        self.cfg = cfg
        d, V = cfg.d_model, cfg.vocab_size
        P, R, C = cfg.n_prelude, cfg.n_core, cfg.n_coda
        kv_dim = cfg.n_kv_head * cfg.head_dim

        self.embed = nn.Embedding(V, d)
        self.value_embeds = nn.ModuleList(nn.Embedding(V, kv_dim) for _ in range(cfg.n_value_embeds))
        if cfg.smear:
            self.smear_gate = zero_init(nn.Linear(12, 1, bias=False))
            self.smear_lambda = nn.Parameter(torch.zeros(1))
        self.rope = Rotary(cfg.head_dim, cfg.rope_frac, cfg.rope_base, cfg.max_seq_len)

        nve = cfg.n_value_embeds
        self.prelude = nn.ModuleList(
            Block(cfg, cfg.layer_kind(i), sandwich=False, use_ve=i < nve, is_first=i == 0)
            for i in range(P))
        self.core = nn.ModuleList(
            Block(cfg, cfg.layer_kind(P + i), sandwich=True, use_ve=False, is_first=False)
            for i in range(R))
        self.coda = nn.ModuleList(
            Block(cfg, cfg.layer_kind(P + R + j), sandwich=False, use_ve=(C - 1 - j) < nve,
                  is_first=False)
            for j in range(C))
        self.adapter = nn.Linear(2 * d, d, bias=False)
        self.skip_lambdas = nn.Parameter(torch.zeros(C)) if cfg.unet_skips else None
        self.lm_head = zero_init(nn.Linear(d, V, bias=False))

        init_linear_(self)
        for ve in self.value_embeds:
            nn.init.normal_(ve.weight, std=0.5)
        self._rng = random.Random(seed)
        self.checkpoint_core = False  # activation checkpointing for grad-tracked loops

    # ------------------------------------------------------------------ utils

    def param_counts(self) -> dict:
        n = lambda ps: sum(p.numel() for p in ps)
        emb = n(self.embed.parameters()) + n(self.value_embeds.parameters())
        head = n(self.lm_head.parameters())
        blocks = n(self.prelude.parameters()) + n(self.core.parameters()) + n(self.coda.parameters())
        total = n(self.parameters())
        return dict(total=total, embeddings=emb, lm_head=head, blocks=blocks,
                    core=n(self.core.parameters()), other=total - emb - head - blocks)

    def flops_per_token(self, T: int, r: float | None = None, k: int | None = None) -> float:
        """Approximate training FLOPs/token (6N rule + attention) at mean loop r,
        backprop depth k. No-grad loops cost only the 2N forward."""
        cfg = self.cfg
        r = cfg.mean_recurrence if r is None else r
        k = min(cfg.backprop_depth, r) if k is None else k
        per_layer = sum(p.numel() for p in self.core[0].parameters())
        attn = 2 * cfg.n_head * cfg.head_dim * T  # QK^T + AV per token, fwd, causal-halved x2
        outer = (cfg.n_prelude + cfg.n_coda) * (per_layer + attn)
        core_layer = per_layer + attn
        head = self.lm_head.weight.numel()
        adapter = self.adapter.weight.numel()
        fwd = 2 * (outer + head + r * (cfg.n_core * core_layer + adapter))
        bwd = 4 * (outer + head + k * (cfg.n_core * core_layer + adapter))
        return fwd + bwd

    def sample_num_steps(self, mean: float | None = None) -> int:
        """Log-normal Poisson loop count with mean ~= ``mean`` (default: the
        config's mean_recurrence; the trainer passes a ramped value)."""
        cfg = self.cfg
        mean = cfg.mean_recurrence if mean is None else mean
        if not cfg.sample_recurrence or mean <= 1:
            return max(1, round(mean))
        sigma = cfg.recurrence_sigma
        mu = math.log(mean - 1) - sigma ** 2 / 2
        tau = math.exp(self._rng.gauss(mu, sigma))
        # Poisson sample via inversion (python-only; keeps all ranks in lockstep)
        L, p, n = math.exp(-tau), 1.0, 0
        while True:
            p *= self._rng.random()
            if p <= L or n > 4 * cfg.max_recurrence:
                break
            n += 1
        return max(1, min(n + 1, cfg.max_recurrence))

    # ------------------------------------------------------------- sub-graphs

    def _layer_cache(self, cache: ModelCache | None, key, block: Block):
        if cache is None:
            return None
        cfg = self.cfg
        if block.kind == "D":
            return cache.get(key, lambda: DeltaCache(cache.B, cfg.n_head, cfg.head_dim,
                                                     cfg.head_dim, block.mixer.qkv_dim,
                                                     block.mixer.conv_k, cache.device,
                                                     cache.dtype))
        return cache.get(key, lambda: KVCache(cache.B, cfg.n_kv_head, cache.T_max, cfg.head_dim,
                                              cache.device, cache.dtype))

    def embed_tokens(self, idx, embed_override=None, override_mask=None, cache=None):
        x = self.embed(idx)
        if embed_override is not None:
            x = torch.where(override_mask[..., None], embed_override.to(x.dtype), x)
        x = rms_norm(x)
        if self.cfg.smear:
            B, T, d = x.shape
            if cache is not None and cache.pos > 0 and cache.smear_prev is not None:
                prev = cache.smear_prev.to(x.dtype)
            else:
                prev = x.new_zeros(B, 1, d)
            shifted = torch.cat([prev, x[:, :-1]], dim=1)
            if cache is not None:
                cache.smear_prev = x[:, -1:].detach()
            gate = torch.sigmoid(self.smear_gate(x[..., :12]))
            x = x + self.smear_lambda.to(x.dtype) * gate * shifted
        return x

    def _core_step(self, s, e, pos0, v_first, cache, i):
        x = self.adapter(torch.cat([s, e], dim=-1))
        slot = i % cache.n_slots if cache is not None else 0
        for j, blk in enumerate(self.core):
            x, _ = blk(x, self.rope, pos0, v_first=v_first,
                       cache=self._layer_cache(cache, ("c", j, slot), blk))
        return x

    def _coda(self, s, skips, ves, pos0, v_first, cache):
        x = s
        P, nve = self.cfg.n_prelude, self.cfg.n_value_embeds
        for j, blk in enumerate(self.coda):
            if self.skip_lambdas is not None and P - 1 - j >= 0:
                x = x + self.skip_lambdas[j].to(x.dtype) * skips[P - 1 - j]
            ve_i = len(self.coda) - 1 - j
            x, _ = blk(x, self.rope, pos0, v_first=v_first,
                       ve=ves[ve_i] if ve_i < nve else None,
                       cache=self._layer_cache(cache, ("d", j), blk))
        return rms_norm(x)

    def logits(self, h):
        z = self.lm_head(h).float()
        c = self.cfg.logit_softcap
        return c * torch.tanh(z / c) if c else z

    def _ce_sum(self, h, t):
        return F.cross_entropy(self.logits(h), t, ignore_index=-1, reduction="sum")

    def lm_loss(self, h, targets, mtp_weights=None, chunk_tokens: int = 8192):
        """Cross-entropy over the (huge, fp32) logits in checkpointed chunks so the
        full [B*T, V] matrix never lives in memory. Optional same-head
        multi-token-prediction aux targets (modded-nanogpt record #53 style):
        mtp_weights[i] weights predicting token t+2+i from position t."""

        def _ce(hh, tt):
            hf, tf = hh.reshape(-1, hh.size(-1)), tt.reshape(-1)
            total = hf.new_zeros((), dtype=torch.float32)
            for i in range(0, hf.size(0), chunk_tokens):
                if torch.is_grad_enabled():
                    total = total + checkpoint(self._ce_sum, hf[i:i + chunk_tokens],
                                               tf[i:i + chunk_tokens], use_reentrant=False)
                else:
                    total = total + self._ce_sum(hf[i:i + chunk_tokens], tf[i:i + chunk_tokens])
            return total / (tf != -1).sum().clamp(min=1)

        loss = _ce(h, targets)
        if mtp_weights:
            for off, w in enumerate(mtp_weights, start=1):
                if w > 0 and targets.size(1) > off:
                    loss = loss + w * _ce(h[:, :-off], targets[:, off:])
        return loss

    # ---------------------------------------------------------------- forward

    def forward(self, idx, targets=None, *, num_steps: int | None = None,
                embed_override=None, override_mask=None, cache: ModelCache | None = None,
                init_state: str | None = None, return_hidden: bool = False,
                exit_threshold: float | None = None, exit_criterion: str = "kl",
                min_steps: int = 1, mtp_weights=None, last_only: bool = False):
        """Returns a dict with ``loss`` (if targets), ``logits`` (if no targets),
        ``hidden`` (if return_hidden) and ``steps`` (loops actually run)."""
        cfg = self.cfg
        B, T = idx.shape
        pos0 = cache.pos if cache is not None else 0

        # ---- prelude
        x = self.embed_tokens(idx, embed_override, override_mask, cache)
        ves = [ve(idx) for ve in self.value_embeds]
        v_first, skips = None, []
        for i, blk in enumerate(self.prelude):
            x, v = blk(x, self.rope, pos0, ve=ves[i] if i < len(ves) else None,
                       v_first=v_first, cache=self._layer_cache(cache, ("p", i), blk))
            if i == 0:
                v_first = v
            skips.append(x)
        e = rms_norm(x)

        # ---- recurrent core
        if num_steps is None:
            num_steps = self.sample_num_steps() if self.training else cfg.mean_recurrence
        mode = init_state or ("random" if self.training else "zero")
        if mode == "random":
            s = torch.randn_like(e).clamp_(-3, 3) * cfg.state_init_std
        else:
            s = torch.zeros_like(e)

        steps_run = 0
        if self.training:
            n_grad = min(cfg.backprop_depth, num_steps)
            with torch.no_grad():
                for i in range(num_steps - n_grad):
                    s = self._core_step(s, e, pos0, v_first, cache, i)
            for i in range(num_steps - n_grad, num_steps):
                if self.checkpoint_core and cache is None:
                    s = checkpoint(self._core_step, s, e, pos0, v_first, None, i,
                                   use_reentrant=False)
                else:
                    s = self._core_step(s, e, pos0, v_first, cache, i)
            steps_run = num_steps
        else:
            adaptive = exit_threshold is not None and T == 1
            logp_prev = None
            for i in range(num_steps):
                s_prev, s = s, self._core_step(s, e, pos0, v_first, cache, i)
                steps_run = i + 1
                if not adaptive or steps_run < min_steps:
                    continue
                if exit_criterion == "latent":
                    rel = (s - s_prev).float().norm(dim=-1) / s.float().norm(dim=-1).clamp(min=1e-6)
                    if rel.max().item() < exit_threshold:
                        break
                else:  # KL(p_i || p_{i-1}) of the next-token distribution
                    h = self._coda(s, skips, ves, pos0, v_first, cache)
                    logp = F.log_softmax(self.logits(h[:, -1]), dim=-1)
                    if logp_prev is not None:
                        kl = (logp.exp() * (logp - logp_prev)).sum(-1)
                        if kl.max().item() < exit_threshold:
                            break
                    logp_prev = logp

        if cache is not None and steps_run < cache.n_slots:
            # Huginn-style sharing: slots this token never reached get its final state.
            last = (steps_run - 1) % cache.n_slots
            for slot in range(steps_run, cache.n_slots):
                for j in range(len(self.core)):
                    src = cache.layers.get(("c", j, last))
                    dst = self._layer_cache(cache, ("c", j, slot), self.core[j])
                    dst.copy_from(src, pos0, T)

        # ---- coda + head
        h = self._coda(s, skips, ves, pos0, v_first, cache)
        if cache is not None:
            cache.pos += T

        out = {"steps": steps_run}
        if return_hidden:
            out["hidden"] = h
        if targets is not None:
            out["loss"] = self.lm_loss(h, targets, mtp_weights)
        else:
            out["logits"] = self.logits(h[:, -1:] if last_only else h)
        return out

    # ------------------------------------------------------------- inference

    def new_cache(self, batch_size: int, max_len: int, n_slots: int | None = None,
                  dtype=None) -> ModelCache:
        dev = self.embed.weight.device
        dtype = dtype or (torch.bfloat16 if dev.type == "cuda" else torch.float32)
        n_slots = n_slots or self.cfg.max_recurrence
        return ModelCache(batch_size, max_len, n_slots, dev, dtype)

    @torch.no_grad()
    def generate(self, idx, max_new_tokens: int, *, temperature: float = 1.0,
                 top_k: int | None = None, num_steps: int | None = None,
                 exit_threshold: float | None = None, exit_criterion: str = "kl",
                 n_slots: int | None = None, eos_token: int | None = None):
        """Sample with a KV cache. ``num_steps`` is the loop budget per token;
        with ``exit_threshold`` each token stops early once its prediction
        (KL) or latent state ("latent") has converged. Returns (tokens, steps
        used per generated token)."""
        self.eval()
        num_steps = num_steps or self.cfg.mean_recurrence
        B, T0 = idx.shape
        cache = self.new_cache(B, T0 + max_new_tokens, n_slots or num_steps)
        out = self(idx, num_steps=num_steps, cache=cache, last_only=True)
        steps_used = []
        for _ in range(max_new_tokens):
            logits = out["logits"][:, -1].float()
            if temperature <= 0:
                nxt = logits.argmax(-1, keepdim=True)
            else:
                logits = logits / temperature
                if top_k:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float("inf")
                nxt = torch.multinomial(F.softmax(logits, dim=-1), 1)
            idx = torch.cat([idx, nxt], dim=1)
            if eos_token is not None and (nxt == eos_token).all():
                break
            if idx.size(1) >= T0 + max_new_tokens:
                break
            out = self(nxt, num_steps=num_steps, cache=cache, last_only=True,
                       exit_threshold=exit_threshold, exit_criterion=exit_criterion)
            steps_used.append(out["steps"])
        return idx, steps_used
