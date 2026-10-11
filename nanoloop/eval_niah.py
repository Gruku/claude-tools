"""Measure *usable* context: needle-in-a-haystack retrieval + loss by position.

  python eval_niah.py runs/long/ckpt_final.pt --lengths 1024,2048,4096,8192,16384
  python eval_niah.py runs/base/ckpt_final.pt --rope-scaling yarn --rope-factor 4   # training-free extension

NIAH: real web text (a held-out val shard) with 1-4 inserted "special magic
number" facts; the model must complete the queried one. Uses held-out words
never seen in synthetic training data. Reported as a length x depth grid.

Loss by position: mean next-token loss per position bucket on long val
sequences. If far buckets are *lower* than near ones the model uses the extra
context; if they rise, the context is nominal.
"""

from __future__ import annotations

import argparse
import glob
import random
from contextlib import nullcontext

import numpy as np
import torch

from nanoloop.checkpoint import gpt2_tokenizer, load_model
from nanoloop.data import load_shard
from nanoloop.longctx import HELD_OUT, needle_example


@torch.no_grad()
def niah_grid(model, enc, hay, lengths, depths, trials, steps, amp, seed=0):
    rng = random.Random(seed)
    grid = {}
    for L in lengths:
        for d in depths:
            hits = 0
            for _ in range(trials):
                toks, gold = needle_example(rng, enc, hay, L, depth=d, words=HELD_OUT, with_answer=False)
                idx = torch.tensor([toks], device=model.embed.weight.device)
                with amp:
                    out, _ = model.generate(idx, 8, temperature=0, num_steps=steps)
                hits += gold in enc.decode([t for t in out[0, len(toks):].tolist() if t < enc.n_vocab])
            grid[(L, d)] = hits / trials
    return grid


@torch.no_grad()
def loss_by_position(model, hay, L, n_seqs, steps, amp, buckets):
    dev = model.embed.weight.device
    sums = np.zeros(len(buckets))
    counts = np.zeros(len(buckets))
    rng = random.Random(1)
    for _ in range(n_seqs):
        s = rng.randrange(0, len(hay) - L - 2)
        seq = torch.tensor(hay[s:s + L + 1].astype(np.int64), device=dev)[None]
        with amp:
            out = model(seq[:, :-1], num_steps=steps, return_hidden=True, last_only=True)
            nll = -model.token_logprobs(out["hidden"], seq[:, 1:])[0].float().cpu().numpy()
        for i, (a, b) in enumerate(buckets):
            if a < L:
                sums[i] += nll[a:min(b, L)].sum()
                counts[i] += len(nll[a:min(b, L)])
    return [s / c if c else float("nan") for s, c in zip(sums, counts)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--lengths", default="1024,2048,4096,8192,16384")
    ap.add_argument("--depths", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--trials", type=int, default=4)
    ap.add_argument("--haystack", default="data/fineweb10B/*_val_*.bin",
                    help="held-out token shard (val split) used as filler and for the loss curve")
    ap.add_argument("--steps", type=int, default=None, help="loops per token")
    ap.add_argument("--rope-scaling", choices=["none", "ntk", "yarn"], default=None)
    ap.add_argument("--rope-factor", type=float, default=None)
    ap.add_argument("--ppl-seqs", type=int, default=8, help="sequences for the loss-by-position curve (0=off)")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    model = load_model(a.ckpt, a.device)
    lengths = [int(x) for x in a.lengths.split(",")]
    depths = [float(x) for x in a.depths.split(",")]
    need = max(lengths) + 64
    trained = model.cfg.context_len or model.cfg.max_seq_len
    kw = {}
    if a.rope_scaling:
        kw = dict(rope_scaling=a.rope_scaling, rope_factor=a.rope_factor or need / trained,
                  rope_orig_len=trained)
    model.set_context(max_seq_len=max(need, model.cfg.max_seq_len), **kw)
    enc = gpt2_tokenizer()
    files = sorted(glob.glob(a.haystack))
    if not files:
        raise SystemExit(f"no haystack shard matches {a.haystack!r}")
    hay = np.asarray(load_shard(files[0]))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if a.device.startswith("cuda") else nullcontext()
    steps = a.steps or model.cfg.mean_recurrence
    print(f"loops={steps} trained context={trained} rope={model.cfg.rope_scaling} "
          f"x{model.cfg.rope_factor:g} table={model.cfg.max_seq_len}")

    grid = niah_grid(model, enc, hay, lengths, depths, a.trials, steps, amp)
    print("\nNIAH accuracy (rows: context length, cols: needle depth)")
    print("length  " + "  ".join(f"{d:>5.2f}" for d in depths) + "   mean")
    for L in lengths:
        row = [grid[(L, d)] for d in depths]
        print(f"{L:>6}  " + "  ".join(f"{x:>5.2f}" for x in row) + f"   {sum(row) / len(row):.2f}")

    if a.ppl_seqs:
        Lmax = max(lengths)
        edges = [0] + [L for L in lengths if L <= Lmax]
        buckets = list(zip(edges[:-1], edges[1:]))
        losses = loss_by_position(model, hay, Lmax, a.ppl_seqs, steps, amp, buckets)
        print("\nloss by position (lower in far buckets = context is being used)")
        for (lo, hi), l in zip(buckets, losses):
            print(f"  tokens {lo:>6}-{hi:<6} {l:.4f}")


if __name__ == "__main__":
    main()
