"""Constrained tool-calling turns and a small agent loop.

A turn decodes freely in text mode. When the model emits <|tool_call|> the
decoder switches to constrained mode:

    forced  {"name":"          <- canonical prefix (same token split as training)
    name    restricted to registered tool names (+ closing quote)
    forced  ,"arguments":
    args    any token that keeps the text a valid JSON-object prefix
    forced  } <|/tool_call|>

so every call parses and names a real tool. Constraints are checked against the
top-k candidates in logit order (rejection over top-k), which keeps decoding
cheap on a 50k vocabulary. Inline calculator spans are executed by the engine.

The agent loop is deliberately short (default 3 steps): at ~200M parameters the
model can pick a tool and fill arguments on familiar phrasing, but not plan
long multi-step trajectories (docs/RESEARCH.md §7).
"""

from __future__ import annotations

import json

import torch
import torch.nn.functional as F

from .chat import CALL_ARGS, CALL_PREFIX, decode, render_prompt
from .config import (CALC, END_CALC, END_OUT, END_TOOL_CALL, END_TURN, GPT2_EOT, OUT,
                     SPECIAL_TOKENS, TOOL_CALL)
from .engine import calc_injection
from .tools import json_close, json_prefix_state, run_tool_call

_TOKSTR: dict = {}


def _tok_str(enc, t):
    key = (id(enc), t)
    s = _TOKSTR.get(key)
    if s is None:
        s = _TOKSTR[key] = enc.decode([t]) if t < enc.n_vocab else ""
    return s


def _pick(logits, valid, temperature, top_k=256):
    """Highest-probability (or sampled) token among the top-k that passes
    `valid`; falls back to scanning the whole vocabulary (rare for a trained
    model, but it guarantees the constraint never dead-ends)."""
    vals, ids = torch.topk(logits, min(top_k, logits.numel()))
    keep = [(v, i) for v, i in zip(vals.tolist(), ids.tolist()) if valid(i)]
    if not keep and top_k < logits.numel():
        vals, ids = torch.sort(logits, descending=True)
        for v, i in zip(vals.tolist(), ids.tolist()):
            if valid(i):
                keep = [(v, i)]
                break
    if not keep:
        return None
    if temperature <= 0:
        return keep[0][1]
    v = torch.tensor([x[0] for x in keep]) / temperature
    return keep[int(torch.multinomial(F.softmax(v, -1), 1))][1]


def parse_assistant_tokens(enc, tokens):
    """Generated assistant tokens -> (content parts, tool calls)."""
    parts, calls, buf, i = [], [], [], 0

    def flush():
        if buf:
            parts.append({"type": "text", "text": decode(enc, buf)})
            buf.clear()

    while i < len(tokens):
        t = tokens[i]
        if t == CALC:
            flush()
            j = tokens.index(END_CALC, i) if END_CALC in tokens[i:] else len(tokens)
            expr = decode(enc, tokens[i + 1:j])
            res = ""
            if j + 1 < len(tokens) and tokens[j + 1] == OUT:
                k = tokens.index(END_OUT, j) if END_OUT in tokens[j:] else len(tokens)
                res, j = decode(enc, tokens[j + 2:k]), k
            parts.append({"type": "calc", "expr": expr, "result": res})
            i = j + 1
        elif t == TOOL_CALL:
            flush()
            j = tokens.index(END_TOOL_CALL, i) if END_TOOL_CALL in tokens[i:] else len(tokens)
            try:
                calls.append(json.loads(decode(enc, tokens[i + 1:j])))
            except ValueError:
                pass
            i = j + 1
        elif t in (END_TURN, GPT2_EOT):
            break
        else:
            buf.append(t)
            i += 1
    flush()
    return parts, calls


@torch.no_grad()
def generate_turn(model, enc, prompt_ids, *, tool_names=(), num_steps=None, max_new=256,
                  temperature=0.0, calculator=True, force_call=False, max_arg_chars=256):
    """Generate one assistant turn. Returns dict(tokens, parts, calls, text).
    ``force_call`` starts the turn inside a tool call (OpenAI tool_choice="required")."""
    model.eval()
    dev = model.embed.weight.device
    num_steps = num_steps or model.cfg.mean_recurrence
    max_new = max(1, min(max_new, model.cfg.max_seq_len - len(prompt_ids) - 16))
    cache = model.new_cache(1, len(prompt_ids) + max_new + 64, n_slots=num_steps)

    def feed(t):
        return model(torch.tensor([[t]], device=dev), num_steps=num_steps, cache=cache,
                     last_only=True, init_state="zero")

    out = model(torch.tensor([prompt_ids], device=dev), num_steps=num_steps, cache=cache,
                last_only=True, init_state="zero")
    allow_calls = bool(tool_names)
    names = list(tool_names)
    specials = set(SPECIAL_TOKENS) | {GPT2_EOT}
    text_ok = {END_TURN, CALC} | ({TOOL_CALL} if allow_calls else set())
    tokens, pending, mode = [], [], "text"
    name_buf = args_buf = ""
    if force_call and allow_calls:
        pending, mode = [TOOL_CALL] + enc.encode_ordinary(CALL_PREFIX), "name"

    for _ in range(max_new):
        if pending:
            t = pending.pop(0)
        else:
            logits = out["logits"][0, -1].float()
            nv = enc.n_vocab  # rows >= n_vocab are padding/special: never plain text
            if mode == "text":
                t = _pick(logits, lambda i: (i < nv and i not in specials) or i in text_ok, temperature)
            elif mode == "calc":
                t = _pick(logits, lambda i: (i < nv and i not in specials) or i == END_CALC, temperature)
            elif mode == "name":
                def ok_name(i):
                    if i >= nv or i in specials or not _tok_str(enc, i):
                        return False
                    s = name_buf + _tok_str(enc, i)
                    return any(n.startswith(s) or s == n + '"' for n in names)
                t = _pick(logits, ok_name, temperature)
            elif mode == "args":
                def ok_args(i):
                    if i >= nv or i in specials or not _tok_str(enc, i):
                        return False
                    s = args_buf + _tok_str(enc, i)
                    return s.lstrip()[:1] in ("", "{") and json_prefix_state(s)[0]
                t = _pick(logits, ok_args, temperature)
            else:  # after a call: another call (max 4 per turn) or end of turn
                n_calls = tokens.count(END_TOOL_CALL)
                t = _pick(logits, lambda i: i == END_TURN or (i == TOOL_CALL and n_calls < 4),
                          temperature)
            if t is None:  # constraint unsatisfiable within top-k: end the turn cleanly
                t = END_TURN
                if mode in ("name", "args"):
                    tokens = tokens[:len(tokens) - tokens[::-1].index(TOOL_CALL) - 1]
                    pending = []
            # --- state transitions driven by generated tokens
            if mode == "name" and t != END_TURN:
                name_buf += _tok_str(enc, t)
                if name_buf.endswith('"') and name_buf[:-1] in names:
                    pending = enc.encode_ordinary(CALL_ARGS)
                    mode = "args"
                    args_buf = ""
            elif mode == "args" and t != END_TURN:
                args_buf += _tok_str(enc, t)
                if json_prefix_state(args_buf)[1]:
                    pending = enc.encode_ordinary("}") + [END_TOOL_CALL]
                    mode = "post_call"
                elif len(args_buf) > max_arg_chars or len(tokens) > max_new - 24:
                    # over budget: close the JSON deterministically rather than emit a broken call
                    pending = enc.encode_ordinary(json_close(args_buf) + "}") + [END_TOOL_CALL]
                    mode = "post_call"
            elif t == TOOL_CALL:
                pending = enc.encode_ordinary(CALL_PREFIX)
                mode, name_buf = "name", ""
            elif t == CALC:
                mode = "calc"
            elif t == END_CALC and mode == "calc":
                tokens.append(t)
                out = feed(t)
                pending = calc_injection(enc, tokens) if calculator else []
                mode = "text"
                continue
        tokens.append(t)
        if t in (END_TURN, GPT2_EOT) and not pending:
            break
        out = feed(t)
    parts, calls = parse_assistant_tokens(enc, tokens)
    text = "".join(p["text"] if p["type"] == "text" else f'{p["expr"]}={p["result"]}' for p in parts)
    return dict(tokens=tokens, parts=parts, calls=calls, text=text.strip())


def run_agent(model, enc, messages, tools: dict, *, max_steps=3, num_steps=None, max_new=256,
              temperature=0.0, on_event=None):
    """ReAct-lite loop: generate, execute any tool calls, feed results back.
    The final step disallows tool calls so the model must answer. Returns the
    updated message list."""
    messages = list(messages)
    budget = model.cfg.max_seq_len - min(max_new, 128) - 16
    for step in range(max_steps):
        allow = step < max_steps - 1
        prompt = render_prompt(enc, messages)
        while len(prompt) > budget:  # drop the oldest non-system turn, keep the latest one
            drop = next((i for i, m in enumerate(messages[:-1]) if m["role"] != "system"), None)
            if drop is None:
                raise ValueError(f"prompt ({len(prompt)} tokens) exceeds the context budget ({budget}); "
                                 "use fewer/shorter tool schemas")
            messages.pop(drop)
            prompt = render_prompt(enc, messages)
        res = generate_turn(model, enc, prompt, tool_names=list(tools) if allow else (),
                            num_steps=num_steps, max_new=max_new, temperature=temperature)
        messages.append(dict(role="assistant", content=res["parts"], tool_calls=res["calls"] or None))
        if on_event:
            on_event("assistant", res)
        if not res["calls"]:
            break
        for call in res["calls"]:
            result = run_tool_call(call, tools)[:500]
            messages.append(dict(role="tool", content=result))
            if on_event:
                on_event("tool", dict(call=call, result=result))
    return messages
