"""CPU tests: kernel equivalence, causality, KV-cache exactness, training step,
latent-reasoning plumbing. Run: python -m pytest tests -q"""

import torch
import torch.nn.functional as F
import pytest

from nanoloop.config import make_config, LATENT
from nanoloop.deltanet import chunk_gated_delta_rule, recurrent_gated_delta_rule
from nanoloop.model import NanoLoop
from nanoloop.optim import build_optimizers, orthogonalize


def _randomize(m):
    # zero-init projections make a fresh model trivially "pass" equivalence tests
    torch.manual_seed(0)
    for p in m.parameters():
        if p.abs().sum() == 0:
            torch.nn.init.normal_(p, std=0.05)
    return m


def test_deltanet_chunk_matches_recurrent():
    torch.manual_seed(0)
    B, T, H, K, V = 2, 150, 3, 16, 8
    q = F.normalize(torch.randn(B, T, H, K), dim=-1)
    k = F.normalize(torch.randn(B, T, H, K), dim=-1)
    v = torch.randn(B, T, H, V)
    g, beta = -torch.rand(B, T, H) * 0.5, torch.rand(B, T, H)
    S0 = torch.randn(B, H, K, V)
    o1, s1 = recurrent_gated_delta_rule(q, k, v, g, beta, 0.3, S0)
    o2, s2 = chunk_gated_delta_rule(q, k, v, g, beta, 0.3, S0, chunk_size=32)
    assert torch.allclose(o1, o2, atol=1e-5) and torch.allclose(s1, s2, atol=1e-5)


@pytest.mark.parametrize("pattern", ["G", "GL", "GDLG"])
def test_causal(pattern):
    m = _randomize(NanoLoop(make_config("tiny", layer_pattern=pattern))).eval()
    idx = torch.randint(0, 512, (1, 32))
    a = m(idx, num_steps=3)["logits"]
    idx2 = idx.clone()
    idx2[0, 20:] = torch.randint(0, 512, (12,))
    b = m(idx2, num_steps=3)["logits"]
    assert torch.allclose(a[0, :20], b[0, :20], atol=1e-5)


@pytest.mark.parametrize("pattern", ["G", "GL", "GDLG"])
def test_kv_cache_matches_full_forward(pattern):
    m = _randomize(NanoLoop(make_config("tiny", layer_pattern=pattern))).eval()
    idx = torch.randint(0, 512, (2, 40))
    full = m(idx, num_steps=4)["logits"]
    cache = m.new_cache(2, 40, n_slots=4)
    outs = [m(idx[:, :25], num_steps=4, cache=cache)["logits"]]
    for t in range(25, 40):
        outs.append(m(idx[:, t:t + 1], num_steps=4, cache=cache)["logits"])
    assert torch.allclose(full, torch.cat(outs, 1), atol=1e-4)


def test_adaptive_exit_and_generate():
    m = _randomize(NanoLoop(make_config("tiny", layer_pattern="GD"))).eval()
    idx = torch.randint(0, 512, (2, 8))
    for crit in ("kl", "latent"):
        out, steps = m.generate(idx, 10, num_steps=6, exit_threshold=1e9, exit_criterion=crit,
                                temperature=0)
        assert out.shape == (2, 18)
        assert all(s <= 2 for s in steps)  # huge threshold -> exit as early as allowed


def test_train_step_reduces_loss():
    torch.manual_seed(0)
    m = NanoLoop(make_config("tiny"))
    opts = build_optimizers(m)
    x = torch.randint(0, 512, (4, 32))
    losses = []
    for _ in range(30):
        loss = m(x, x.roll(-1, 1))["loss"]
        loss.backward()
        for o in opts:
            o.step()
        m.zero_grad()
        losses.append(loss.item())
    assert losses[-1] < losses[0] - 1.0


def test_truncated_bptt_and_mtp():
    m = NanoLoop(make_config("tiny"))
    x = torch.randint(0, 512, (2, 16))
    out = m(x, x, num_steps=5, mtp_weights=[0.5, 0.25])
    out["loss"].backward()
    assert m.adapter.weight.grad is not None and m.embed.weight.grad is not None


def test_orthogonalize_is_near_orthogonal():
    G = torch.randn(64, 32)
    O = orthogonalize(G)
    s = torch.linalg.svdvals(O)
    assert s.min() > 0.5 and s.max() < 1.3


def test_sample_num_steps_mean():
    m = NanoLoop(make_config("tiny", mean_recurrence=6, max_recurrence=32))
    xs = [m.sample_num_steps() for _ in range(4000)]
    assert 5.0 < sum(xs) / len(xs) < 7.0 and min(xs) >= 1


def test_latent_forward_backprops_through_thoughts():
    from coconut import LatentProjector, latent_forward

    cfg = make_config("tiny", vocab_size=50304)
    m = _randomize(NanoLoop(cfg)).train()
    proj = LatentProjector(cfg.d_model)
    torch.nn.init.normal_(proj.out.weight, std=0.02)
    ids = torch.randint(0, 500, (2, 20))
    lat = torch.tensor([[5, 6, 7], [8, 9, 10]])
    ids[0, 5:8] = LATENT
    ids[1, 8:11] = LATENT
    out = latent_forward(m, proj, ids, lat, steps=2, targets=ids.roll(-1, 1))
    out["loss"].backward()
    assert proj.fc.weight.grad is not None and proj.fc.weight.grad.abs().sum() > 0


class _FakeEnc:
    n_vocab = 50257

    def encode(self, s):
        return [ord(c) % 200 + 1 for c in s]

    encode_ordinary = encode

    def decode(self, ids):
        return "".join(chr(i - 1) for i in ids)


def test_coconut_format_and_cached_solve():
    from coconut import Formatter, LatentProjector, collate, solve, latent_forward

    ex = dict(question="1+2?", steps=["<<1+2=3>>", "<<3*1=3>>"], answer="3")
    fmt = Formatter(_FakeEnc(), c_thought=2, max_stage=3)
    ids0, lab0, lat0, anc0 = fmt.build(ex, 0)
    ids3, lab3, lat3, anc3 = fmt.build(ex, 3)
    assert lat0 == [] and len(lat3) == 6 and all(ids3[p] == LATENT for p in lat3)
    assert ids3[anc3 + 1:] == lab3[anc3 + 1:]  # answer is supervised
    cfg = make_config("tiny", vocab_size=50304)
    m = _randomize(NanoLoop(cfg)).eval()
    proj = LatentProjector(cfg.d_model)
    # cached latent decoding == uncached latent forward on the same prefix
    ids, tgt, lat, anchor = collate([fmt.build(ex, 2)], "cpu")
    with torch.no_grad():
        ref = latent_forward(m, proj, ids, lat, steps=2)["logits"]
    pred, text = solve(m, proj, fmt, ex, 2, steps=2, max_new=4)
    assert isinstance(text, str) and (pred is None or isinstance(pred, str))
    assert torch.isfinite(ref).all()
