"""GSM8k-Aug loader (whynlp/gsm8k-aug: ~385k GPT-4-augmented GSM8K problems with
equation-only reasoning steps, the dataset used by iCoT, Coconut and CODI)."""

from __future__ import annotations

import re


def load_gsm8k_aug(split: str = "train"):
    from datasets import load_dataset

    ds = load_dataset("whynlp/gsm8k-aug", split=split)
    out = []
    for row in ds:
        steps = row.get("steps")
        if steps is None:  # CODI/iCoT format: "<<a*b=c>> <<c+d=e>>"
            cot = row.get("cot") or row.get("rationale") or ""
            steps = re.findall(r"<<[^>]*>>", cot) or [s for s in cot.split("\n") if s.strip()]
        out.append(dict(question=row["question"].strip(), steps=[s.strip() for s in steps],
                        answer=str(row["answer"]).strip().replace(",", "")))
    return out
