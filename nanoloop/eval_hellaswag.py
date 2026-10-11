"""HellaSwag (val, 10,042 items) completion-style eval, acc_norm as in llm.c /
nanoGPT: pick the ending with the lowest mean per-token loss.

Reference: GPT-2 124M = 29.4 (OpenAI) / 29.9 (llm.c 10B tokens); SmolLM2-135M = 42.1.

  python eval_hellaswag.py runs/<run>/ckpt_final.pt --steps 1,4,8,16
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from contextlib import nullcontext

import torch
import torch.nn.functional as F

from nanoloop.checkpoint import gpt2_tokenizer, load_model

URL = "https://raw.githubusercontent.com/rowanz/hellaswag/master/data/hellaswag_val.jsonl"


def load_examples(cache_dir):
    path = os.path.join(cache_dir, "hellaswag_val.jsonl")
    if not os.path.exists(path):
        os.makedirs(cache_dir, exist_ok=True)
        urllib.request.urlretrieve(URL, path)
    with open(path) as f:
        return [json.loads(line) for line in f]


def render(enc, ex):
    ctx = enc.encode(ex["ctx"])
    rows, masks = [], []
    for end in ex["endings"]:
        e = enc.encode(" " + end)
        rows.append(ctx + e)
        masks.append([0] * len(ctx) + [1] * len(e))
    T = max(len(r) for r in rows)
    tok = torch.zeros(4, T, dtype=torch.long)
    mask = torch.zeros(4, T, dtype=torch.long)
    for i, (r, m) in enumerate(zip(rows, masks)):
        tok[i, :len(r)] = torch.tensor(r)
        mask[i, :len(m)] = torch.tensor(m)
    return tok, mask, int(ex["label"])


@torch.no_grad()
def score(model, enc, examples, steps, device, amp):
    correct = 0
    for ex in examples:
        tok, mask, label = render(enc, ex)
        tok, mask = tok.to(device), mask.to(device)
        with amp:
            logits = model(tok, num_steps=steps)["logits"]
        losses = F.cross_entropy(logits[:, :-1].flatten(0, 1).float(), tok[:, 1:].flatten(),
                                 reduction="none").view(4, -1)
        m = mask[:, 1:].float()
        avg = (losses * m).sum(1) / m.sum(1)
        correct += int(avg.argmin().item() == label)
    return correct / len(examples)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--steps", default=None, help="comma-separated loop counts (default: training mean)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--cache-dir", default="data/hellaswag")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    model = load_model(a.ckpt, a.device)
    enc = gpt2_tokenizer()
    examples = load_examples(a.cache_dir)[: a.limit]
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if a.device.startswith("cuda") else nullcontext()
    steps = [int(s) for s in a.steps.split(",")] if a.steps else [model.cfg.mean_recurrence]
    for r in steps:
        acc = score(model, enc, examples, r, a.device, amp)
        print(f"hellaswag acc_norm @ r={r}: {acc * 100:.2f}% ({len(examples)} examples)", flush=True)


if __name__ == "__main__":
    main()
