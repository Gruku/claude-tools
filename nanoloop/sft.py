"""Supervised finetuning in the chat template (post-training stages B and C).

  # B: general chat SFT (nanochat-style mixture, smol-smoltalk sized for <1B models)
  python sft.py --init runs/base/ckpt_final_avg.pt --mix smoltalk:1,mmlu:1,gsm8k:4 --out-dir runs/sft
  # C: task SFT on GSM8k-Aug explicit CoT (the base for RFT / RL / Coconut)
  python sft.py --init runs/sft/ckpt_final.pt --mix gsm8k-aug:3 --out-dir runs/sft-math

Choices (docs/RESEARCH.md §5): loss on assistant tokens only; conversations are
packed best-fit into fixed rows and padded, never cropped; the loop count stays
randomised exactly as in pretraining so test-time depth scaling survives; the
pretraining optimizer state is warm-started with a lower LR (nanochat).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from contextlib import nullcontext

import torch

from nanoloop.chat import build_mixture, render_conversation
from nanoloop.checkpoint import gpt2_tokenizer, load_checkpoint
from nanoloop.config import GPT2_EOT, SPECIAL_TOKENS
from nanoloop.engine import gsm8k_accuracy
from nanoloop.optim import build_optimizers


def init_special_tokens(model):
    """Set never-trained special-token rows to the mean of the real vocabulary."""
    with torch.no_grad():
        ids = torch.tensor(sorted(SPECIAL_TOKENS), device=model.embed.weight.device)
        for table in [model.embed, *model.value_embeds]:
            table.weight[ids] = table.weight[:GPT2_EOT].mean(0)
        model.lm_head.weight[ids] = model.lm_head.weight[:GPT2_EOT].mean(0)


def pack(convs, enc, seq_len, seed=0):
    """Best-fit-decreasing pack of tokenised conversations into rows of
    seq_len+1 tokens (padding the remainder). Over-long conversations are
    dropped, never cropped. Returns a list of (ids, mask) rows."""
    rng = random.Random(seed)
    docs = [render_conversation(enc, c["messages"]) for c in convs]
    docs = [d for d in docs if len(d[0]) <= seq_len + 1 and sum(d[1]) > 0]
    docs.sort(key=lambda d: -len(d[0]))
    cap = seq_len + 1
    rows, by_free = [], [[] for _ in range(cap + 1)]  # by_free[c] = rows with c tokens free
    for ids, mask in docs:
        n = len(ids)
        c = next((c for c in range(n, cap + 1) if by_free[c]), None)
        if c is None or c == cap:
            rows.append(([], []))
            r, c = len(rows) - 1, cap
        else:
            r = by_free[c].pop()
        rows[r][0].extend(ids)
        rows[r][1].extend(mask)
        by_free[c - n].append(r)
    rng.shuffle(rows)
    return rows


def to_batch(rows, seq_len, device):
    x = torch.full((len(rows), seq_len), GPT2_EOT, dtype=torch.long)
    y = torch.full((len(rows), seq_len), -1, dtype=torch.long)
    for b, (ids, mask) in enumerate(rows):
        ids_t = torch.tensor(ids[:seq_len + 1])
        m = torch.tensor(mask[:seq_len + 1])
        n = len(ids_t) - 1
        x[b, :n] = ids_t[:-1]
        y[b, :n] = torch.where(m[1:] == 1, ids_t[1:], torch.tensor(-1))
    return x.to(device), y.to(device)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", required=True)
    ap.add_argument("--mix", default="smoltalk:1,mmlu:1,gsm8k:4", help="source:epochs,...")
    ap.add_argument("--out-dir", default="runs/sft")
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--device-batch", type=int, default=8)
    ap.add_argument("--batch-rows", type=int, default=32, help="rows per optimizer step")
    ap.add_argument("--lr-scale", type=float, default=0.5, help="x pretraining LRs")
    ap.add_argument("--warmup-frac", type=float, default=0.03)
    ap.add_argument("--val-rows", type=int, default=64)
    ap.add_argument("--eval-every", type=int, default=200)
    ap.add_argument("--gsm8k-eval", type=int, default=200, help="GSM8K test items per eval (0=off)")
    ap.add_argument("--limit", type=int, default=None, help="cap rows per source (debugging)")
    ap.add_argument("--fresh-optim", action="store_true", help="don't warm-start optimizer state")
    ap.add_argument("--no-compile", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    is_cuda = a.device.startswith("cuda")
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if is_cuda else nullcontext()
    enc = gpt2_tokenizer()
    model, ck = load_checkpoint(a.init, a.device)
    if not ck.get("chat_init"):
        init_special_tokens(model)
    model.train()

    convs = build_mixture(a.mix, seed=a.seed, limit=a.limit)
    rows = pack(convs, enc, a.seq_len, seed=a.seed)
    val_rows, rows = rows[:a.val_rows], rows[a.val_rows:]
    steps = math.ceil(len(rows) / a.batch_rows)
    accum = a.batch_rows // a.device_batch
    print(f"{len(convs):,} conversations -> {len(rows):,} packed rows -> {steps} steps")

    optims = build_optimizers(model, lr_scale=a.lr_scale)
    lrs = [[g["initial_lr"] for g in o.param_groups] for o in optims]
    if ck.get("optims") and not a.fresh_optim:
        for o, s in zip(optims, ck["optims"]):
            try:
                o.load_state_dict(s)
            except (ValueError, KeyError):
                print("optimizer state incompatible; starting fresh")
                break
        for o, group_lrs in zip(optims, lrs):  # loaded state carries old LRs; reset
            for g, lr in zip(o.param_groups, group_lrs):
                g["lr"] = g["initial_lr"] = lr
    if is_cuda and not a.no_compile:
        for blk in [*model.prelude, *model.core, *model.coda]:
            blk.compile(dynamic=False)

    gsm_test = []
    if a.gsm8k_eval:
        from nanoloop.chat import load_source
        gsm_test = load_source("gsm8k", "test")[: a.gsm8k_eval]
    os.makedirs(a.out_dir, exist_ok=True)
    logf = open(os.path.join(a.out_dir, "log.jsonl"), "a")

    def log(rec):
        print(" ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in rec.items()), flush=True)
        logf.write(json.dumps(rec) + "\n")
        logf.flush()

    def evaluate(step):
        model.eval()
        tot = 0.0
        with torch.no_grad(), amp:
            for i in range(0, len(val_rows), a.device_batch):
                x, y = to_batch(val_rows[i:i + a.device_batch], a.seq_len, a.device)
                tot += model(x, y)["loss"].item()
        rec = dict(step=step, val_loss=tot / max(1, math.ceil(len(val_rows) / a.device_batch)))
        if gsm_test:
            rec["gsm8k"] = gsm8k_accuracy(model, enc, gsm_test, model.cfg.mean_recurrence,
                                          "cuda" if is_cuda else "cpu")
        model.train()
        log(rec)

    t0 = time.time()
    for step in range(steps):
        warm = max(1, int(steps * a.warmup_frac))
        m = (step + 1) / warm if step < warm else 1 - (step - warm) / max(1, steps - warm)
        for o in optims:
            for g in o.param_groups:
                g["lr"] = g["initial_lr"] * m
        batch = rows[step * a.batch_rows:(step + 1) * a.batch_rows]
        loss_acc = 0.0
        for i in range(0, len(batch), a.device_batch):
            x, y = to_batch(batch[i:i + a.device_batch], a.seq_len, a.device)
            with amp:
                loss = model(x, y)["loss"]
            (loss / max(1, accum)).backward()
            loss_acc += loss.item() / max(1, accum)
        for o in optims:
            o.step()
        model.zero_grad(set_to_none=True)
        if step % 10 == 0:
            log(dict(step=step, loss=loss_acc, lr_mult=m, elapsed=round(time.time() - t0)))
        if (step + 1) % a.eval_every == 0 or step == steps - 1:
            evaluate(step + 1)

    path = os.path.join(a.out_dir, "ckpt_final.pt")
    torch.save(dict(model=model.state_dict(), optims=[o.state_dict() for o in optims],
                    config=model.cfg.to_dict(), chat_init=True, stage=f"sft:{a.mix}"), path)
    print(f"saved {path}")


if __name__ == "__main__":
    main()
