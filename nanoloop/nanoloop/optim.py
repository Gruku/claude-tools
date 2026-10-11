"""Optimizers: Muon (Polar Express + NorMuon + cautious weight decay) for hidden
matrices, AdamW for embeddings / head / scalars.

Hidden 2-D matrices are where Muon wins (~1.4x over tuned AdamW at 0.1B,
arXiv 2509.02046). Note the weight-shared core: its gradient is the sum over
the k back-propagated loops, which Muon's orthogonalisation makes scale-free.
"""

from __future__ import annotations

import torch
import torch.nn as nn

# Polar Express (arXiv 2505.16932): per-iteration optimal quintic coefficients,
# 5 iterations, as used by modded-nanogpt and nanochat.
POLAR_EXPRESS = (
    (8.1566, -22.4833, 15.8788),
    (4.0429, -2.8089, 0.5000),
    (3.8917, -2.7725, 0.5061),
    (3.2858, -2.3681, 0.4645),
    (2.3465, -1.7098, 0.4232),
)


@torch.no_grad()
def orthogonalize(G: torch.Tensor) -> torch.Tensor:
    """Approximate the polar factor U V^T of G."""
    X = G.bfloat16() if G.is_cuda else G.float()
    transposed = X.size(-2) > X.size(-1)
    if transposed:
        X = X.mT
    X = X / (X.norm(dim=(-2, -1), keepdim=True) * (1 + 2e-2) + 1e-6)
    for a, b, c in POLAR_EXPRESS:
        A = X @ X.mT
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    if transposed:
        X = X.mT
    return X.to(G.dtype)


class Muon(torch.optim.Optimizer):
    def __init__(self, params, lr=0.02, momentum=0.95, beta2=0.95, weight_decay=0.2):
        super().__init__(params, dict(lr=lr, momentum=momentum, beta2=beta2,
                                      weight_decay=weight_decay))

    @torch.no_grad()
    def step(self):
        for group in self.param_groups:
            lr, mom, beta2, wd = group["lr"], group["momentum"], group["beta2"], group["weight_decay"]
            for p in group["params"]:
                if p.grad is None:
                    continue
                g = p.grad
                st = self.state[p]
                if not st:
                    st["buf"] = torch.zeros_like(g)
                    st["v"] = torch.zeros(g.size(0), device=g.device, dtype=torch.float32)
                buf = st["buf"]
                buf.lerp_(g, 1 - mom)
                u = g.lerp(buf, mom)  # Nesterov
                O = orthogonalize(u).float()
                # NorMuon (arXiv 2510.05491): per-neuron second-moment normalisation,
                # then restore the orthogonalised update's overall norm.
                st["v"].lerp_(O.square().mean(dim=-1), 1 - beta2)
                n0 = O.norm()
                O = O * st["v"].clamp_min(1e-10).rsqrt()[:, None]
                O = O * (n0 / O.norm().clamp_min(1e-10))
                O = O * max(1.0, p.size(0) / p.size(1)) ** 0.5
                if wd:
                    # Cautious weight decay (arXiv 2510.12402): only decay where the
                    # update already pushes the weight toward zero.
                    mask = (O * p.float()) > 0
                    p.mul_(1 - lr * wd * mask.to(p.dtype))
                p.add_(O.to(p.dtype), alpha=-lr)


def build_optimizers(model: nn.Module, *, muon_lr=0.02, muon_wd=0.2, embed_lr=0.3,
                     value_embed_lr=0.15, head_lr=0.008, scalar_lr=0.04, hc_lr=0.004,
                     ngram_lr=0.1, lr_scale=1.0):
    """Partition parameters. Muon never touches embeddings, head, 1-D params,
    hyper-connection gates or n-gram tables (Qwen3.8 / DeepSeek V4 practice:
    Muon for true weight matrices only, AdamW for routing/gating parameters)."""
    muon, embed, vembed, head, scalars, hc, ngram = [], [], [], [], [], [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if name.startswith("ngram.table"):
            ngram.append(p)
        elif ".gr_" in name or name.startswith("collapse_"):
            hc.append(p)
        elif name.startswith("embed."):
            embed.append(p)
        elif name.startswith("value_embeds."):
            vembed.append(p)
        elif name.startswith("lm_head."):
            head.append(p)
        elif p.ndim == 2 and min(p.shape) > 16:
            muon.append(p)
        else:
            scalars.append(p)
    adam_groups = [
        dict(params=embed, lr=embed_lr * lr_scale, betas=(0.8, 0.95)),
        dict(params=vembed, lr=value_embed_lr * lr_scale, betas=(0.8, 0.95)),
        dict(params=head, lr=head_lr * lr_scale, betas=(0.8, 0.95)),
        dict(params=scalars, lr=scalar_lr * lr_scale, betas=(0.9, 0.99)),
        dict(params=hc, lr=hc_lr * lr_scale, betas=(0.9, 0.95)),
        dict(params=ngram, lr=ngram_lr * lr_scale, betas=(0.8, 0.95)),
    ]
    adam_groups = [g for g in adam_groups if g["params"]]
    fused = next(model.parameters()).is_cuda
    adam = torch.optim.AdamW(adam_groups, eps=1e-10, weight_decay=0.0, fused=fused)
    opt_muon = Muon(muon, lr=muon_lr * lr_scale, weight_decay=muon_wd)
    for opt in (adam, opt_muon):
        for g in opt.param_groups:
            g["initial_lr"] = g["lr"]
    return [adam, opt_muon]
