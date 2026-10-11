"""Chat template, answer extraction and the post-training data sources.

Template (one conversation):
    <|endoftext|> [<|system|> text <|end|>] <|user|> text <|end|> <|assistant|> text <|end|> ...
Loss is applied to assistant text and its closing <|end|> only.
"""

from __future__ import annotations

import random
import re

from .config import ASSISTANT, END_TURN, GPT2_EOT, SPECIAL_TOKENS, SYSTEM, USER

ROLE_TOKEN = {"system": SYSTEM, "user": USER, "assistant": ASSISTANT}


def render_conversation(enc, messages):
    """Returns (ids, mask) where mask marks tokens the model is trained on."""
    ids, mask = [GPT2_EOT], [0]
    for m in messages:
        role = m["role"]
        if role not in ROLE_TOKEN:
            continue
        body = enc.encode_ordinary(m["content"])
        train = 1 if role == "assistant" else 0
        ids += [ROLE_TOKEN[role]] + body + [END_TURN]
        mask += [0] + [train] * (len(body) + 1)
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
    if name == "mmlu":  # auxiliary_train: ~100k multiple-choice items (RACE, ARC, OBQA, ...)
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
