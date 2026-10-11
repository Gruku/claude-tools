"""Long-context pieces: RoPE scaling, set_context, synthetic retrieval, NIAH eval."""

import random

import numpy as np
import torch

from nanoloop.config import make_config
from nanoloop.layers import Rotary
from nanoloop.model import NanoLoop
from test_model import _FakeEnc, _randomize


def test_rope_scaling_variants():
    base = Rotary(64, 0.5, 10000, 256)
    same = Rotary(64, 0.5, 10000, 256, "yarn", 1.0, 128)
    assert torch.equal(base.cos, same.cos) and same.attn_factor == 1.0
    yarn = Rotary(64, 0.5, 10000, 256, "yarn", 4.0, 2048)
    ntk = Rotary(64, 0.5, 10000, 256, "ntk", 4.0, 128)
    # highest-frequency dim (index 0) is kept by YaRN; the lowest is interpolated
    assert torch.allclose(yarn.cos[:, 0], base.cos[:, 0]) and not torch.allclose(yarn.cos[:, -1], base.cos[:, -1])
    assert yarn.attn_factor > 1.0 and not torch.allclose(ntk.cos, base.cos)


def test_set_context_extends_and_keeps_cache_exact():
    m = _randomize(NanoLoop(make_config("tiny", layer_pattern="GC"))).eval()
    m.set_context(max_seq_len=1024, rope_scaling="yarn", rope_factor=4.0, rope_orig_len=256)
    idx = torch.randint(0, 512, (1, 600))
    full = m(idx, num_steps=2)["logits"]
    cache = m.new_cache(1, 600, n_slots=2)
    outs = [m(idx[:, :590], num_steps=2, cache=cache)["logits"]]
    for t in range(590, 600):
        outs.append(m(idx[:, t:t + 1], num_steps=2, cache=cache)["logits"])
    assert torch.allclose(full, torch.cat(outs, 1), atol=1e-4)


def test_loop_long_preset_builds_and_is_cheaper_at_long_context():
    long, base = NanoLoop(make_config("loop-long")), NanoLoop(make_config("loop-base"))
    assert long.flops_per_token(32768) < 0.5 * base.flops_per_token(32768)
    assert sum(b.kind == "G" for b in [*long.prelude, *long.core, *long.coda]) == 3


def test_needle_and_kv_examples():
    from nanoloop.longctx import kv_example, needle_example, synth_retrieval_stream
    enc = _FakeEnc()
    hay = np.random.default_rng(0).integers(1, 200, 50_000)
    rng = random.Random(0)
    toks, gold = needle_example(rng, enc, hay, 2000, depth=0.5)
    text = enc.decode(toks[1:])
    assert f"is {gold}." in text and text.rstrip().endswith(f"is {gold}.") and abs(len(toks) - 2000) < 50
    toks, v = kv_example(rng, enc, 800)
    assert enc.decode(toks[1:]).endswith(v) and len(toks) <= 800
    gen = synth_retrieval_stream(enc, hay, lengths=(512,))
    assert all(len(next(gen)) <= 520 for _ in range(5))


def test_niah_and_position_loss_run():
    from contextlib import nullcontext
    from eval_niah import loss_by_position, niah_grid
    m = _randomize(NanoLoop(make_config("tiny", vocab_size=50304, max_seq_len=1024))).eval()
    hay = np.random.default_rng(0).integers(1, 200, 20_000)
    grid = niah_grid(m, _FakeEnc(), hay, [256], [0.0, 1.0], 1, 2, nullcontext())
    assert set(grid) == {(256, 0.0), (256, 1.0)}
    losses = loss_by_position(m, hay, 512, 1, 2, nullcontext(), [(0, 256), (256, 512)])
    assert all(np.isfinite(losses))
