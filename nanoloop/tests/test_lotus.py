"""LOTUS parallel latent workspace."""

import torch

from nanoloop.config import END_LATENT, LATENT, PAD_STEP, START_LATENT, make_config
from nanoloop.model import NanoLoop
from test_model import _FakeEnc, _randomize

EX = dict(question="2+3*4?", steps=["<<3*4=12>>", "<<2+12=14>>"], answer="14")


def test_targets_align_slots_and_answer():
    from lotus import Formatter
    enc = _FakeEnc()
    fmt = Formatter(enc, K=3, c=12)
    ids, tgt, (s, e) = fmt.build(EX)
    assert ids[s - 1] == START_LATENT and ids[e] == END_LATENT and all(t == LATENT for t in ids[s:e])
    assert tgt[s:s + 10] == enc.encode("<<3*4=12>>") and tgt[s + 10] == PAD_STEP
    assert all(t == PAD_STEP for t in tgt[s + 24:e])  # third block: empty step
    assert tgt[e:-1] == ids[e + 1:] and tgt[-1] == -1 and all(t == -1 for t in tgt[:s])


def test_step_overflow_folds_into_last_block():
    from lotus import Formatter
    fmt = Formatter(_FakeEnc(), K=1, c=30)
    blocks = fmt.step_targets(EX)
    assert len(blocks) == 1 and blocks[0][:21] == _FakeEnc().encode("<<3*4=12>><<2+12=14>>")


def test_lotus_loss_trains_slots_and_solve_runs():
    from lotus import Formatter, LatentSlots, collate, lotus_loss, solve
    enc = _FakeEnc()
    cfg = make_config("tiny", vocab_size=50304)
    m = _randomize(NanoLoop(cfg)).train()
    fmt = Formatter(enc, K=2, c=12)
    slots = LatentSlots(cfg.d_model, 2, 12)
    ids, tgt, spans = collate([fmt.build(EX), fmt.build(dict(EX, question="what is 2+3*4"))], "cpu")
    loss, l_ans, l_lat, _ = lotus_loss(m, slots, ids, tgt, spans, steps=3, deep_weight=0.3)
    loss.backward()
    assert slots.block_pos.grad.abs().sum() > 0 and torch.isfinite(loss)
    pred, trace = solve(m, slots, fmt, EX, steps=2)
    assert len(trace) == 2
    pred0, trace0 = solve(m, slots, fmt, EX, steps=2, n_blocks=0)  # shortcut test path
    assert trace0 == []
