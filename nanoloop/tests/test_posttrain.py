"""Post-training stack: chat template, packing, sampling engine, RL loss, merging, mixtures."""

import numpy as np
import torch

from nanoloop.chat import extract_answer, render_conversation, render_prompt
from nanoloop.config import ASSISTANT, END_TURN, USER, make_config
from nanoloop.data import MixtureLoader, TokenLoader, write_shard
from nanoloop.engine import sample_group
from nanoloop.model import NanoLoop
from test_model import _FakeEnc, _randomize


def _tiny(vocab=50304):
    return _randomize(NanoLoop(make_config("tiny", vocab_size=vocab)))


def test_render_conversation_masks_assistant_only():
    enc = _FakeEnc()
    msgs = [dict(role="user", content="hi"), dict(role="assistant", content="yo")]
    ids, mask = render_conversation(enc, msgs)
    assert ids[1] == USER and ids[-1] == END_TURN
    trained = [t for t, m in zip(ids, mask) if m]
    assert trained == enc.encode("yo") + [END_TURN]
    assert render_prompt(enc, msgs[:1])[-1] == ASSISTANT


def test_extract_answer():
    assert extract_answer("so 3+4=7\n#### 7") == "7"
    assert extract_answer("#### 1,234.") == "1234"
    assert extract_answer("#### -2.50") == "-2.5"
    assert extract_answer("no marker 5") is None


def test_pack_and_batch_preserve_supervision():
    from sft import pack, to_batch
    enc = _FakeEnc()
    convs = [dict(messages=[dict(role="user", content="q" * (i % 7 + 1)),
                            dict(role="assistant", content="a" * (i % 5 + 1))]) for i in range(50)]
    rows = pack(convs, enc, seq_len=40)
    assert all(len(r[0]) <= 41 for r in rows)
    n_sup = sum(sum(render_conversation(enc, c["messages"])[1]) for c in convs)
    assert sum(sum(r[1]) for r in rows) == n_sup  # nothing cropped or lost
    x, y = to_batch(rows, 40, "cpu")
    assert x.shape == y.shape == (len(rows), 40)
    # every supervised target sits right after its input position
    assert (y != -1).sum().item() == n_sup - sum(r[1][0] for r in rows)


def test_sample_group_shapes_and_stop():
    m = _tiny().eval()
    outs = sample_group(m, [1, 2, 3], G=4, max_new=6, num_steps=2, temperature=1.0)
    assert len(outs) == 4 and all(1 <= len(o) <= 6 for o in outs)
    greedy = sample_group(m, [1, 2, 3], G=3, max_new=5, num_steps=2, temperature=0)
    assert greedy[0] == greedy[1] == greedy[2]


def test_policy_loss_with_per_loop_credit():
    import argparse
    from rl import policy_loss
    m = _tiny().train()
    seqs = [([1, 2, 3], [4, 5, END_TURN], 0.5), ([1, 2, 3], [6, END_TURN], -0.5)]
    for credit in ("final", "all"):
        m.zero_grad()
        a = argparse.Namespace(device_batch=2, loop_credit=credit)
        loss = policy_loss(m, seqs, a, 4, "cpu", torch.autocast("cpu", enabled=False), norm=10)
        assert np.isfinite(loss)
        assert m.adapter.weight.grad is not None and m.adapter.weight.grad.abs().sum() > 0


def test_loop_readout_count():
    m = _tiny().train()
    x = torch.randint(0, 500, (1, 8))
    out = m(x, num_steps=5, return_hidden=True, loop_readout=True, last_only=True)
    assert len(out["loop_hidden"]) == m.cfg.backprop_depth
    assert torch.equal(out["loop_hidden"][-1], out["hidden"])


def test_token_logprobs_matches_log_softmax():
    m = _tiny().eval()
    x = torch.randint(0, 500, (2, 8))
    out = m(x, num_steps=2, return_hidden=True)
    y = x.roll(-1, 1)
    y[:, -1] = -1
    lp = m.token_logprobs(out["hidden"], y)
    ref = torch.log_softmax(out["logits"], -1).gather(-1, y.clamp(min=0)[..., None]).squeeze(-1)
    assert torch.allclose(lp[:, :-1], ref[:, :-1], atol=1e-5) and (lp[:, -1] == 0).all()


def test_merge_state_dicts():
    from merge import merge_state_dicts
    a, b = {"w": torch.ones(2)}, {"w": torch.zeros(2)}
    assert torch.allclose(merge_state_dicts([a, b], [0.875, 0.125])["w"], torch.full((2,), 0.875))


def test_mixture_loader(tmp_path):
    for name, val in (("a", 1), ("b", 2)):
        (tmp_path / name).mkdir()
        write_shard(str(tmp_path / name / f"{name}_train_000001.bin"), np.full(10_000, val))
    la = TokenLoader(str(tmp_path / "a" / "*_train_*.bin"), 2, 8)
    lb = TokenLoader(str(tmp_path / "b" / "*_train_*.bin"), 2, 8)
    mix = MixtureLoader([la, lb], [0.8, 0.2], seed=0)
    firsts = [mix.next_batch()[0][0, 0].item() for _ in range(500)]
    frac_a = firsts.count(1) / len(firsts)
    assert 0.72 < frac_a < 0.88
    st = mix.state_dict()
    nxt = [mix.next_batch()[0][0, 0].item() for _ in range(20)]
    mix.load_state_dict(st)
    assert [mix.next_batch()[0][0, 0].item() for _ in range(20)] == nxt


def test_constrained_tool_call_is_always_valid():
    from nanoloop.agent import generate_turn, parse_assistant_tokens
    from nanoloop.tools import BUILTIN_TOOLS
    enc = _FakeEnc()
    names = list(BUILTIN_TOOLS)
    for seed in range(3):
        torch.manual_seed(seed)
        m = _tiny().eval()
        res = generate_turn(m, enc, [1, 2, 3], tool_names=names, num_steps=2, max_new=300,
                            temperature=1.0, force_call=True)
        assert res["calls"], "constrained decoding must complete a call"
        for call in res["calls"]:
            assert call["name"] in names and isinstance(call["arguments"], dict)


def test_parse_assistant_tokens_roundtrip():
    from nanoloop.agent import parse_assistant_tokens
    from nanoloop.chat import render_conversation
    enc = _FakeEnc()
    msg = dict(role="assistant", content=[{"type": "text", "text": "a="},
                                          {"type": "calc", "expr": "2*3", "result": "6"}],
               tool_calls=[{"name": "word_count", "arguments": {"text": "x y"}}])
    ids, _ = render_conversation(enc, [msg])
    parts, calls = parse_assistant_tokens(enc, ids[2:])
    assert parts == msg["content"] and calls == msg["tool_calls"]


def test_json_prefix_and_calculator():
    from nanoloop.tools import calculate, json_prefix_state as j
    assert j('{"a":[1,{"b":null}]}') == (True, True)
    assert j('{"a":1') == (True, False) and j('{"a" 1')[0] is False and j('{"a":01')[0] is False
    assert calculate("48/2") == "24" and calculate("2**10") == "error"
    assert calculate("__import__('os')") == "error" and calculate("7/3") == "2.333333"


def test_engine_forces_calculator_output():
    from nanoloop.config import CALC, END_CALC, OUT, END_OUT
    from nanoloop.engine import calc_injection, _forced_mask
    enc = _FakeEnc()
    row = [5, CALC] + enc.encode("6*7") + [END_CALC]
    inj = calc_injection(enc, row)
    assert inj == [OUT] + enc.encode("42") + [END_OUT]
    assert _forced_mask(row + inj + [9]) == [0] * len(row) + [1] * len(inj) + [0]


def test_run_agent_loop_smoke():
    from nanoloop.agent import run_agent
    from nanoloop.tools import BUILTIN_TOOLS
    enc = _FakeEnc()
    m = _randomize(NanoLoop(make_config("tiny", vocab_size=50304, max_seq_len=2048))).eval()
    events = []
    msgs = [dict(role="system", content="", tools=list(BUILTIN_TOOLS.values())),
            dict(role="user", content="What is 6*7?")]
    out = run_agent(m, enc, msgs, BUILTIN_TOOLS, max_steps=2, num_steps=2, max_new=40,
                    on_event=lambda kind, payload: events.append(kind))
    assert out[-1]["role"] == "assistant" and not out[-1].get("tool_calls")
    assert events.count("assistant") >= 1
