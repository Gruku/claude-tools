"""Chat template, answer extraction and the post-training data sources.

Template (one conversation):
    <|endoftext|> [<|system|> text <|end|>] <|user|> text <|end|>
    <|assistant|> text [<|calc|>48/2<|/calc|><|out|>24<|/out|> text]
                  [<|tool_call|>{"name":"f","arguments":{...}}<|/tool_call|>] <|end|>
    <|tool|><|tool_response|>...<|/tool_response|><|end|>  <|assistant|> ... <|end|>

Messages follow the OpenAI shape: {"role", "content", "tool_calls": [{"name",
"arguments"}]}; assistant "content" may also be a list of parts
({"type": "text", "text"} / {"type": "calc", "expr", "result"}). A system
message may carry "tools": [Tool or schema dict].

Loss is applied to assistant-written tokens only: text, calculator
expressions, tool calls and the closing <|end|>. System/user turns, tool
responses and calculator outputs (which the engine injects) are never trained on.
"""

from __future__ import annotations

import random
import re

import json

from .config import (ASSISTANT, CALC, END_CALC, END_OUT, END_TOOL_CALL, END_TOOL_RESPONSE,
                     END_TURN, GPT2_EOT, OUT, SPECIAL_TOKENS, SYSTEM, TOOL, TOOL_CALL,
                     TOOL_RESPONSE, USER)

ROLE_TOKEN = {"system": SYSTEM, "user": USER, "assistant": ASSISTANT, "tool": TOOL}

# Tool calls are tokenised piecewise so training sees exactly the token
# boundaries the constrained decoder produces at inference.
CALL_PREFIX, CALL_ARGS = '{"name":"', ',"arguments":'


def encode_tool_call(enc, call: dict):
    args = json.dumps(call.get("arguments") or {}, separators=(",", ":"), ensure_ascii=False)
    return (enc.encode_ordinary(CALL_PREFIX) + enc.encode_ordinary(call["name"] + '"')
            + enc.encode_ordinary(CALL_ARGS) + enc.encode_ordinary(args) + enc.encode_ordinary("}"))


def _system_text(m):
    text = m.get("content") or ""
    if m.get("tools"):
        from .tools import tools_system_prompt
        tools = [t if hasattr(t, "schema") else _SchemaTool(t) for t in m["tools"]]
        text = (text + "\n\n" if text else "") + tools_system_prompt(tools)
    return text


class _SchemaTool:
    def __init__(self, schema):
        self._s = schema

    def schema(self):
        return self._s


def render_conversation(enc, messages):
    """Returns (ids, mask) where mask marks tokens the model is trained on."""
    ids, mask = [GPT2_EOT], [0]

    def add(toks, m):
        ids.extend(toks)
        mask.extend([m] * len(toks))

    for m in messages:
        role = m["role"]
        if role not in ROLE_TOKEN:
            continue
        if role == "assistant":
            add([ASSISTANT], 0)
            content = m.get("content") or ""
            parts = content if isinstance(content, list) else [{"type": "text", "text": content}]
            for p in parts:
                if p.get("type") == "calc":
                    add([CALC] + enc.encode_ordinary(p["expr"]) + [END_CALC], 1)
                    add([OUT] + enc.encode_ordinary(str(p["result"])) + [END_OUT], 0)
                elif p.get("text"):
                    add(enc.encode_ordinary(p["text"]), 1)
            for call in m.get("tool_calls") or []:
                add([TOOL_CALL] + encode_tool_call(enc, call) + [END_TOOL_CALL], 1)
            add([END_TURN], 1)
        elif role == "tool":
            add([TOOL, TOOL_RESPONSE] + enc.encode_ordinary(str(m.get("content", ""))[:2000])
                + [END_TOOL_RESPONSE, END_TURN], 0)
        else:
            text = _system_text(m) if role == "system" else m.get("content") or ""
            add([ROLE_TOKEN[role]] + enc.encode_ordinary(text) + [END_TURN], 0)
    return ids, mask


def render_prompt(enc, messages):
    """Prompt for generation: the conversation so far (ending on a user turn)
    plus an open assistant turn."""
    ids, _ = render_conversation(enc, messages)
    return ids + [ASSISTANT]


def decode(enc, ids):
    out = []
    for t in ids:
        if t in SPECIAL_TOKENS:
            out.append(SPECIAL_TOKENS[t])
        elif t < enc.n_vocab:
            out.append(enc.decode([t]))
    return "".join(out)


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def extract_answer(text: str) -> str | None:
    """GSM8K-style final answer: the number after the last '####'."""
    if "####" not in text:
        return None
    m = _NUM.search(text.split("####")[-1])
    return normalize_number(m.group(0)) if m else None


def normalize_number(s: str) -> str:
    s = s.replace(",", "").strip().rstrip(".")
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return s


# ----------------------------------------------------------------------------
# Data sources -> list of {"messages": [...], "answer": optional gold}
# ----------------------------------------------------------------------------


def _strip_calc(s: str) -> str:
    return re.sub(r"<<[^>]*>>", "", s)


def load_source(name: str, split: str = "train"):
    from datasets import load_dataset

    if name == "smoltalk":  # SmolLM2-135M/360M-Instruct's SFT set, sized for <1B models
        ds = load_dataset("HuggingFaceTB/smol-smoltalk", split=split)
        return [dict(messages=r["messages"]) for r in ds]
    if name == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split=split)
        out = []
        for r in ds:
            reasoning, ans = r["answer"].split("####")
            out.append(dict(messages=[
                dict(role="user", content=r["question"].strip()),
                dict(role="assistant", content=_strip_calc(reasoning).strip() + f"\n#### {ans.strip()}")],
                answer=normalize_number(ans)))
        return out
    if name == "gsm8k-aug":  # 385k GPT-4-augmented problems, equation-only CoT (iCoT/Coconut/CODI)
        from .gsm8k_aug import load_gsm8k_aug
        out = []
        for ex in load_gsm8k_aug(split):
            body = "\n".join(ex["steps"]) + f"\n#### {ex['answer']}"
            out.append(dict(messages=[dict(role="user", content=ex["question"]),
                                      dict(role="assistant", content=body)],
                            answer=normalize_number(ex["answer"])))
        return out
    if name == "gsm8k-calc":  # GSM8K with <<expr=result>> annotations -> calculator spans (nanochat)
        ds = load_dataset("openai/gsm8k", "main", split=split)
        out = []
        for r in ds:
            reasoning, ans = r["answer"].split("####")
            parts = calc_parts(reasoning.strip()) + [{"type": "text", "text": f"\n#### {ans.strip()}"}]
            out.append(dict(messages=[dict(role="user", content=r["question"].strip()),
                                      dict(role="assistant", content=parts)],
                            answer=normalize_number(ans)))
        return out
    if name == "gsm8k-aug-calc":
        from .gsm8k_aug import load_gsm8k_aug
        out = []
        for ex in load_gsm8k_aug(split):
            parts = []
            for st in ex["steps"]:
                parts += calc_parts(st) + [{"type": "text", "text": "\n"}]
            parts.append({"type": "text", "text": f"#### {ex['answer']}"})
            out.append(dict(messages=[dict(role="user", content=ex["question"]),
                                      dict(role="assistant", content=parts)],
                            answer=normalize_number(ex["answer"])))
        return out
    if name in ("xlam", "hermes", "smoltalk2-tools", "tools-synth"):
        from .tool_data import load_tool_source
        return load_tool_source(name, split)
    if name == "mmlu":  # auxiliary_train: ~100k multiple-choice items (RACE, ARC, OBQA, ...)
        try:
            ds = load_dataset("cais/mmlu", "all", split="auxiliary_train")
        except Exception:
            ds = load_dataset("cais/mmlu", "auxiliary_train", split="train")
        out = []
        for r in ds:
            r = r.get("train", r)
            letters = "ABCD"[: len(r["choices"])]
            opts = "\n".join(f"{l}. {c}" for l, c in zip(letters, r["choices"]))
            out.append(dict(messages=[
                dict(role="user", content=f"{r['question'].strip()}\n\n{opts}\n\nAnswer with the letter."),
                dict(role="assistant", content=letters[int(r["answer"])])]))
        return out
    raise KeyError(f"unknown SFT source {name!r}")


_CALC = re.compile(r"<<([^=<>]+)=([^<>]*)>>")


def calc_parts(text: str):
    """'48/2 = <<48/2=24>>24 clips' -> text / calc(expr, result) / text parts.
    The calculator output is recomputed so training never teaches a wrong value."""
    from .tools import calculate
    parts, pos = [], 0
    for m in _CALC.finditer(text):
        if m.start() > pos:
            parts.append({"type": "text", "text": text[pos:m.start()]})
        expr = m.group(1).strip()
        result = calculate(expr)
        if result == "error":
            result = m.group(2).strip()
        parts.append({"type": "calc", "expr": expr, "result": result})
        pos = m.end()
    if pos < len(text):
        parts.append({"type": "text", "text": text[pos:]})
    return parts


def parse_mix(spec: str):
    """'smoltalk:1,gsm8k:4' -> [('smoltalk', 1.0), ('gsm8k', 4.0)] (epochs per source)."""
    out = []
    for part in spec.split(","):
        name, _, w = part.partition(":")
        out.append((name.strip(), float(w) if w else 1.0))
    return out


def build_mixture(spec: str, seed: int = 0, limit: int | None = None):
    rng = random.Random(seed)
    rows = []
    for name, epochs in parse_mix(spec):
        data = load_source(name)
        if limit:
            data = data[:limit]
        whole, frac = int(epochs), epochs - int(epochs)
        rows += data * whole + rng.sample(data, int(len(data) * frac))
    rng.shuffle(rows)
    return rows
