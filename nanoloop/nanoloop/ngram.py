"""Hashed n-gram memory: Engram (DeepSeek, used in V4.1) / PLE (Qwen3.8-Flash-Next).

For every position, the last 2 and 3 tokens are hashed by several independent
multiplicative-XOR hashes into prime-sized embedding tables. The looked-up
vectors are fused into the residual stream through a context-dependent gate:

    e   = concat_heads Table[hash_{n,k}(t_{i-n+1..i})]           # [E]
    v   = W_v e,   k = RMSNorm(W_k e),   q = RMSNorm(h)
    a   = <k, q> / sqrt(d);   a = sign(a) * sqrt(|a|)               # signed-sqrt gate logit
    h  += sigmoid(a) * v

It adds tens of millions of parameters at ~zero FLOPs (a gather plus two
d x E projections): static local-pattern knowledge moves out of the
transformer, leaving the looped core free for computation. Placed once, at the
prelude output, i.e. right where the loop's input injection is formed.
Contexts reset at <|endoftext|> so n-grams never span documents.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

from .config import GPT2_EOT
from .layers import rms_norm

_MASK63 = (1 << 63) - 1


def _splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & ((1 << 64) - 1)
    return (z ^ (z >> 31)) & _MASK63


def _is_prime(n):
    if n < 2:
        return False
    for p in range(2, int(math.isqrt(n)) + 1):
        if n % p == 0:
            return False
    return True


def _primes_near(n, count):
    out, x = [], n
    while len(out) < count:
        if _is_prime(x):
            out.append(x)
        x += 1
    return out


class NgramMemory(nn.Module):
    def __init__(self, d_model: int, orders=(2, 3), heads_per_order: int = 4, rows: int = 100_003,
                 d_head: int = 64, seed: int = 0):
        super().__init__()
        self.orders = tuple(orders)
        self.max_ctx = max(self.orders) - 1
        n_heads = len(self.orders) * heads_per_order
        primes = _primes_near(rows, n_heads)
        self.register_buffer("primes", torch.tensor(primes, dtype=torch.int64), persistent=False)
        offsets = [0]
        for p in primes[:-1]:
            offsets.append(offsets[-1] + p)
        self.register_buffer("offsets", torch.tensor(offsets, dtype=torch.int64), persistent=False)
        mult, state = [], seed * 1000 + 17
        for n in self.orders:
            for _ in range(heads_per_order):
                row = []
                for _ in range(max(self.orders)):
                    state += 1
                    row.append(_splitmix64(state) | 1)  # odd multipliers
                mult.append(row)
        self.register_buffer("mult", torch.tensor(mult, dtype=torch.int64), persistent=False)
        self.head_order = [n for n in self.orders for _ in range(heads_per_order)]
        self.table = nn.Embedding(sum(primes), d_head)
        nn.init.normal_(self.table.weight, std=1.0)
        E = n_heads * d_head
        self.w_v = nn.Linear(E, d_model, bias=False)
        self.w_k = nn.Linear(E, d_model, bias=False)
        nn.init.zeros_(self.w_v.weight)  # starts as a no-op on the residual stream
        self.d = d_model

    def hash_ids(self, ctx: torch.Tensor) -> torch.Tensor:
        """ctx: [B, L] token ids (L >= T). Returns table rows [B, L, n_heads]."""
        doc = torch.cumsum((ctx == GPT2_EOT).long(), dim=1)
        shifted, same_doc = [ctx], [torch.ones_like(ctx, dtype=torch.bool)]
        for i in range(1, self.max_ctx + 1):
            pad = torch.full_like(ctx[:, :i], -1)
            s = torch.cat([pad, ctx[:, :-i]], dim=1)
            dsh = torch.cat([torch.full_like(doc[:, :i], -1), doc[:, :-i]], dim=1)
            shifted.append(s)
            same_doc.append(dsh == doc)
        out = []
        for h, n in enumerate(self.head_order):
            acc = torch.zeros_like(ctx)
            for i in range(n):
                tok = torch.where(same_doc[i], shifted[i], torch.full_like(ctx, 50257 + i))
                acc = torch.bitwise_xor(acc, tok * self.mult[h, i])
            out.append(torch.remainder(acc, self.primes[h]) + self.offsets[h])
        return torch.stack(out, dim=-1)

    def forward(self, idx, h, prev_ids=None):
        """idx: [B, T] current tokens; h: [B, T, d] hidden; prev_ids: [B, <=max_ctx]
        tokens preceding idx (for cached decoding). Returns the residual update."""
        ctx = idx if prev_ids is None else torch.cat([prev_ids, idx], dim=1)
        rows = self.hash_ids(ctx)[:, -idx.size(1):]
        e = self.table(rows).flatten(-2).to(h.dtype)  # [B, T, E]
        v = self.w_v(e)
        k = rms_norm(self.w_k(e))
        a = (k * rms_norm(h)).sum(-1, keepdim=True) / math.sqrt(self.d)
        a = torch.sign(a) * torch.sqrt(a.abs() + 1e-6)
        return torch.sigmoid(a) * v
