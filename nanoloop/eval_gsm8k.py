"""GSM8K test accuracy of a chat-format checkpoint, swept over loop counts.

  python eval_gsm8k.py runs/grpo/ckpt_final.pt --steps 1,2,4,6,12,24
  python eval_gsm8k.py ckpt.pt --samples 16 --temperature 1.0   # pass@16

Record this curve after every post-training stage: single-depth finetuning can
silently collapse the model's test-time depth scaling.
"""

from __future__ import annotations

import argparse

import torch

from nanoloop.chat import load_source
from nanoloop.checkpoint import gpt2_tokenizer, load_model
from nanoloop.engine import gsm8k_accuracy


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--steps", default=None, help="comma list of loop counts (default: training mean)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max-new", type=int, default=256)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    model = load_model(a.ckpt, a.device)
    enc = gpt2_tokenizer()
    test = load_source("gsm8k", "test")[: a.limit]
    steps = [int(s) for s in a.steps.split(",")] if a.steps else [model.cfg.mean_recurrence]
    dev = "cuda" if a.device.startswith("cuda") else "cpu"
    for r in steps:
        acc = gsm8k_accuracy(model, enc, test, r, dev, a.max_new, a.samples, a.temperature)
        metric = "pass@1" if a.samples == 1 else f"pass@{a.samples}"
        print(f"GSM8K {metric} @ loops={r}: {acc * 100:.2f}% (n={len(test)})", flush=True)


if __name__ == "__main__":
    main()
