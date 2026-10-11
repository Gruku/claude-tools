"""Tool-calling SFT sources converted to the NanoLoop chat schema.

  xlam            Salesforce/xlam-function-calling-60k (gated: accept terms on HF)
  hermes          NousResearch/hermes-function-calling-v1 (single-turn + multi-turn files)
  smoltalk2-tools HuggingFaceTB/smoltalk2 SFT tool-call traces (format parsed best-effort)
  tools-synth     synthetic data for nanoloop.tools.BUILTIN_TOOLS, incl. no-call negatives

At ~200M parameters the per-tool synthetic data matters more than the generic
sets (Octopus / TinyAgent recipe): generic sets teach the format, task data
teaches the tools. Hammer-style function masking (randomised names) is applied
to a fraction of generic examples so the model reads descriptions, not names.
"""

from __future__ import annotations

import ast
import json
import random
import re
import string

from .tools import BUILTIN_TOOLS, calculate

_TC = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
_TR = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.S)
_TOOLS = re.compile(r"<tools>\s*(.*?)\s*</tools>", re.S)


def _loads(s):
    try:
        return json.loads(s)
    except Exception:
        try:
            return ast.literal_eval(s)
        except Exception:
            return None


def _norm_call(c):
    if not isinstance(c, dict) or "name" not in c:
        return None
    args = c.get("arguments", c.get("parameters", {}))
    if isinstance(args, str):
        args = _loads(args) or {}
    return {"name": str(c["name"]), "arguments": args if isinstance(args, dict) else {}}


def _norm_schema(t):
    if isinstance(t, dict) and "function" in t:
        t = t["function"]
    return t if isinstance(t, dict) and "name" in t else None


def _mask_names(ex, rng):
    """Hammer function masking: rename tools consistently to random identifiers."""
    mapping = {}
    for m in ex["messages"]:
        for t in m.get("tools") or []:
            mapping.setdefault(t["name"], "fn_" + "".join(rng.choices(string.ascii_lowercase, k=6)))
    if not mapping:
        return ex
    for m in ex["messages"]:
        if m.get("tools"):
            m["tools"] = [dict(t, name=mapping.get(t["name"], t["name"])) for t in m["tools"]]
        for c in m.get("tool_calls") or []:
            c["name"] = mapping.get(c["name"], c["name"])
    return ex


def _xlam(split, rng, mask_frac=0.3, max_tools=6):
    from datasets import load_dataset
    out = []
    for r in load_dataset("Salesforce/xlam-function-calling-60k", split="train"):
        tools = [_norm_schema(t) for t in (_loads(r["tools"]) or [])]
        calls = [_norm_call(c) for c in (_loads(r["answers"]) or [])]
        if not tools or None in tools or not calls or None in calls or len(tools) > max_tools:
            continue
        ex = dict(messages=[dict(role="system", content="", tools=tools),
                            dict(role="user", content=r["query"]),
                            dict(role="assistant", content="", tool_calls=calls)])
        out.append(_mask_names(ex, rng) if rng.random() < mask_frac else ex)
    return out


def _from_sharegpt(conv, tools_hint=None):
    """ShareGPT / Hermes turns with <tool_call> XML -> chat schema."""
    msgs = []
    for t in conv:
        who, val = t.get("from") or t.get("role"), t.get("value") or t.get("content") or ""
        if who == "system":
            tools = tools_hint
            m = _TOOLS.search(val)
            if m:
                raw = _loads(m.group(1))
                if raw is None:  # one schema per line
                    raw = [_loads(x) for x in m.group(1).splitlines() if x.strip()]
                tools = [x for x in (_norm_schema(y) for y in (raw if isinstance(raw, list) else [raw])) if x]
            msgs.append(dict(role="system", content="" if m else val, tools=tools or None))
        elif who in ("human", "user"):
            msgs.append(dict(role="user", content=val))
        elif who in ("gpt", "assistant"):
            calls = [c for c in (_norm_call(_loads(x)) for x in _TC.findall(val)) if c]
            text = _TC.sub("", val).strip()
            msgs.append(dict(role="assistant", content=text, tool_calls=calls or None))
        elif who in ("tool", "function", "ipython"):
            m = _TR.search(val)
            msgs.append(dict(role="tool", content=(m.group(1) if m else val)[:1500]))
    return msgs if any(m["role"] == "assistant" for m in msgs) else None


def _hermes(split, rng):
    from datasets import load_dataset
    out = []
    for f in ("func-calling-singleturn.json", "func-calling.json"):
        try:
            ds = load_dataset("NousResearch/hermes-function-calling-v1", data_files=f, split="train")
        except Exception:
            continue
        for r in ds:
            msgs = _from_sharegpt(r["conversations"])
            if msgs:
                out.append(dict(messages=msgs))
    return out


def _smoltalk2_tools(split, rng):
    from datasets import load_dataset
    out = []
    for sub in ("xlam_traces_no_think", "hermes_function_calling_v1_no_think"):
        try:
            ds = load_dataset("HuggingFaceTB/smoltalk2", "SFT", split=sub)
        except Exception:
            continue
        for r in ds:
            kw = r.get("chat_template_kwargs") or {}
            tools = kw.get("xml_tools") or kw.get("tools")
            if isinstance(tools, str):
                tools = _loads(tools)
            tools = [x for x in (_norm_schema(t) for t in (tools or [])) if x] or None
            msgs = _from_sharegpt(r["messages"], tools_hint=tools)
            if msgs:
                if tools and not any(m["role"] == "system" for m in msgs):
                    msgs.insert(0, dict(role="system", content="", tools=tools))
                out.append(dict(messages=msgs))
    return out


# --------------------------------------------------------------- synthetic data

_CALC_Q = ["What is {e}?", "Calculate {e}.", "Compute {e} please.", "{e} = ?", "Can you work out {e}?",
           "I need the value of {e}."]
_CONV_Q = ["Convert {v} {f} to {t}.", "How many {t} is {v} {f}?", "What is {v} {f} in {t}?"]
_UNITS = [("km", "mi"), ("mi", "km"), ("kg", "lb"), ("lb", "kg"), ("m", "ft"), ("ft", "m"),
          ("c", "f"), ("f", "c"), ("l", "gal")]
_WC_TEXTS = ["the quick brown fox jumps over the lazy dog", "small models need narrow tasks",
             "loops give the model more time to think", "tools turn guesses into facts"]
_CHAT = [("Hi!", "Hello! How can I help?"), ("What is the capital of France?", "Paris."),
         ("Tell me a fun fact.", "Octopuses have three hearts."),
         ("Thanks!", "You're welcome!"), ("What color is the sky on a clear day?", "Blue.")]


def _expr(rng):
    a, b, c = rng.randint(2, 999), rng.randint(2, 99), rng.randint(2, 50)
    return rng.choice([f"{a}+{b}", f"{a}*{b}", f"{a}-{b}*{c}", f"({a}+{b})/{c}", f"{a}*{b}+{c}"])


def _synth(n, rng):
    tools = list(BUILTIN_TOOLS.values())
    out = []
    for _ in range(n):
        kind = rng.random()
        sys_msg = dict(role="system", content="", tools=rng.sample(tools, k=rng.randint(1, len(tools))))
        names = {t.name for t in sys_msg["tools"]}
        if kind < 0.35 and "calculator" in names:
            e = _expr(rng)
            call = {"name": "calculator", "arguments": {"expression": e}}
            res = calculate(e)
            ans = f"{e} = {res}."
        elif kind < 0.65 and "convert_units" in names:
            f, t = rng.choice(_UNITS)
            v = rng.choice([1, 2, 3, 5, 10, 12, 20, 42, 100])
            call = {"name": "convert_units", "arguments": {"value": v, "from_unit": f, "to_unit": t}}
            res = BUILTIN_TOOLS["convert_units"](**call["arguments"])
            ans = f"{v} {f} is about {res} {t}."
            e = None
        elif kind < 0.85 and "word_count" in names:
            text = rng.choice(_WC_TEXTS)
            call = {"name": "word_count", "arguments": {"text": text}}
            res = BUILTIN_TOOLS["word_count"](**call["arguments"])
            ans = f"That text has {res} words."
            e = None
        else:  # irrelevance / no-call negative (When2Call-style): answer directly
            q, a = rng.choice(_CHAT)
            out.append(dict(messages=[sys_msg, dict(role="user", content=q),
                                      dict(role="assistant", content=a)]))
            continue
        if call["name"] == "calculator":
            q = rng.choice(_CALC_Q).format(e=e)
        elif call["name"] == "convert_units":
            q = rng.choice(_CONV_Q).format(v=call["arguments"]["value"], f=call["arguments"]["from_unit"],
                                           t=call["arguments"]["to_unit"])
        else:
            q = f'How many words are in "{call["arguments"]["text"]}"?'
        out.append(dict(messages=[sys_msg, dict(role="user", content=q),
                                  dict(role="assistant", content="", tool_calls=[call]),
                                  dict(role="tool", content=res),
                                  dict(role="assistant", content=ans)]))
    return out


def load_tool_source(name, split="train", seed=0):
    rng = random.Random(seed)
    if name == "xlam":
        return _xlam(split, rng)
    if name == "hermes":
        return _hermes(split, rng)
    if name == "smoltalk2-tools":
        return _smoltalk2_tools(split, rng)
    if name == "tools-synth":
        return _synth(20000 if split == "train" else 500, rng)
    raise KeyError(name)
