"""Model configuration and named presets.

Every default here is a deliberate choice backed by docs/RESEARCH.md. Presets
exist for ablations, not as a menu of equally-good options.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

# GPT-2 BPE (50257 tokens) padded to a multiple of 128. The padding rows host
# the latent-reasoning special tokens used by stage-2 (see coconut.py).
GPT2_EOT = 50256
START_LATENT = 50257
LATENT = 50258
END_LATENT = 50259


@dataclass
class ModelConfig:
    vocab_size: int = 50304
    d_model: int = 768
    n_head: int = 6
    n_kv_head: int = 6  # < n_head enables GQA
    head_dim: int = 128
    mlp_ratio: float = 4.0  # ReLU^2 MLP

    # --- recurrent depth (Huginn layout: prelude -> core x r -> coda) -------
    n_prelude: int = 2
    n_core: int = 4
    n_coda: int = 2
    mean_recurrence: int = 6  # training mean of the sampled loop count
    backprop_depth: int = 4  # truncated BPTT: grads through the last k loops
    max_recurrence: int = 16  # hard cap on sampled loops (bounds step time)
    recurrence_sigma: float = 0.5  # log-normal-Poisson sigma
    sample_recurrence: bool = True  # False => always mean_recurrence (dense baseline)
    state_init_std: float = 0.6325  # sqrt(2/5): Huginn "like-init" in unit-RMS space

    # --- token mixers --------------------------------------------------------
    # One letter per unique layer (prelude + core + coda), repeated cyclically
    # if shorter: G = global attention, L = sliding-window attention,
    # D = Gated DeltaNet (linear attention).
    layer_pattern: str = "G"
    local_window: int = 512
    rope_frac: float = 0.5  # partial RoPE: rotate half the head dims
    rope_base: float = 10000.0
    attn_scale: float = 0.12  # softmax scale under QK-norm (modded-nanogpt)
    attn_gate: str = "elementwise"  # Qwen gated attention: elementwise|headwise|none
    xsa: bool = True  # gated exclusive self-attention (init as no-op)

    # --- value / embedding pathways ------------------------------------------
    n_value_embeds: int = 2  # tables shared U-net style by prelude[i] / coda[-1-i]
    value_residual: bool = True  # mix layer-0 values into every attention layer
    smear: bool = True  # 1-token lookback gate on the embedding stream
    unet_skips: bool = True  # prelude outputs feed the mirrored coda layer

    logit_softcap: float = 15.0
    max_seq_len: int = 4096  # RoPE table size (inference can exceed training T)

    def __post_init__(self):
        assert self.n_head % self.n_kv_head == 0
        assert self.n_value_embeds <= min(self.n_prelude, self.n_coda) or self.n_value_embeds == 0
        assert set(self.layer_pattern) <= set("GLD"), self.layer_pattern

    @property
    def n_unique_layers(self) -> int:
        return self.n_prelude + self.n_core + self.n_coda

    def layer_kind(self, idx: int) -> str:
        return self.layer_pattern[idx % len(self.layer_pattern)]

    def effective_depth(self, r: int | None = None) -> int:
        r = self.mean_recurrence if r is None else r
        return self.n_prelude + r * self.n_core + self.n_coda

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


PRESETS: dict[str, dict] = {
    # The main bet: ~100M compute-active params, effective depth 28 at r=6.
    "loop-base": {},
    # Dense control: GPT-2-shaped 12 layers, no recurrence (more unique params,
    # ~0.6x the FLOPs/token of loop-base). Compare at equal tokens AND equal FLOPs.
    "dense-base": dict(n_prelude=4, n_core=4, n_coda=4, mean_recurrence=1,
                       backprop_depth=1, sample_recurrence=False),
    # Hybrid linear attention in the loop: 3 Gated DeltaNet : 1 global per core.
    "loop-hybrid": dict(layer_pattern="GG" + "DDDG" + "GG"),
    # nanochat-style sliding windows (3 short : 1 long), for long-context runs.
    "loop-swa": dict(layer_pattern="LG" + "LLLG" + "LG"),
    # Tiny config for CPU smoke tests.
    "tiny": dict(vocab_size=512, d_model=64, n_head=4, n_kv_head=2, head_dim=16,
                 n_prelude=1, n_core=2, n_coda=1, mean_recurrence=3,
                 backprop_depth=2, max_recurrence=6, n_value_embeds=1,
                 local_window=8, max_seq_len=256),
}


def make_config(preset: str = "loop-base", **overrides) -> ModelConfig:
    if preset not in PRESETS:
        raise KeyError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    kw = dict(PRESETS[preset])
    kw.update({k: v for k, v in overrides.items() if v is not None})
    return ModelConfig(**kw)
