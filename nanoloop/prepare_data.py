"""Download / tokenize pretraining data into uint16 shards under data/<name>/.

  # The modded-nanogpt benchmark data (pre-tokenized GPT-2 FineWeb, ~100M tok/shard).
  # Use this val set to compare against the 3.28 "GPT-2 124M" target.
  python prepare_data.py fineweb10B --train-shards 30

  # Higher-quality corpora, tokenized locally with the GPT-2 BPE:
  python prepare_data.py fineweb-edu --max-tokens 5e9
  python prepare_data.py climbmix --max-tokens 5e9
  python prepare_data.py hf --hf-dataset <id> [--hf-config <name>] --text-column text
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os

import numpy as np

from nanoloop.data import write_shard

HF_PRESETS = {
    "fineweb-edu": ("HuggingFaceFW/fineweb-edu", "sample-10BT", "text"),
    "fineweb-edu-100B": ("HuggingFaceFW/fineweb-edu", "sample-100BT", "text"),
    "climbmix": ("karpathy/climbmix-400b-shuffle", None, "text"),
}

_enc = None


def _tokenize(text: str) -> np.ndarray:
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("gpt2")
    ids = [_enc.eot_token] + _enc.encode_ordinary(text)  # EOT delimits documents
    return np.asarray(ids, dtype=np.uint16)


def download_fineweb10B(out_dir: str, train_shards: int) -> None:
    from huggingface_hub import hf_hub_download

    def get(fname):
        if not os.path.exists(os.path.join(out_dir, fname)):
            hf_hub_download(repo_id="kjj0/fineweb10B-gpt2", filename=fname,
                            repo_type="dataset", local_dir=out_dir)

    get("fineweb_val_000000.bin")
    for i in range(1, train_shards + 1):
        get(f"fineweb_train_{i:06d}.bin")


def tokenize_hf(out_dir: str, name: str, dataset: str, config: str | None, text_col: str,
                max_tokens: float, shard_tokens: int, val_tokens: int, workers: int) -> None:
    from datasets import load_dataset

    ds = load_dataset(dataset, name=config, split="train", streaming=True)
    texts = (row[text_col] for row in ds)
    buf = np.empty(shard_tokens, dtype=np.uint16)
    fill, shard, total = 0, 0, 0
    target = val_tokens  # shard 0 is the validation split

    def flush(n):
        nonlocal shard
        split = "val" if shard == 0 else "train"
        write_shard(os.path.join(out_dir, f"{name}_{split}_{shard:06d}.bin"), buf[:n])
        print(f"wrote shard {shard} ({split}, {n:,} tokens, total {total:,})", flush=True)
        shard += 1

    with mp.Pool(workers) as pool:
        for toks in pool.imap(_tokenize, texts, chunksize=64):
            while len(toks):
                take = min(len(toks), target - fill)
                buf[fill:fill + take] = toks[:take]
                fill, toks, total = fill + take, toks[take:], total + take
                if fill == target:
                    flush(fill)
                    fill, target = 0, shard_tokens
            if total >= max_tokens:
                break
    if fill:
        flush(fill)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", choices=["fineweb10B", "hf", *HF_PRESETS])
    ap.add_argument("--out", default="data")
    ap.add_argument("--train-shards", type=int, default=30, help="fineweb10B: 100M tokens each")
    ap.add_argument("--max-tokens", type=float, default=5e9)
    ap.add_argument("--shard-tokens", type=int, default=100_000_000)
    ap.add_argument("--val-tokens", type=int, default=10_485_760)
    ap.add_argument("--hf-dataset")
    ap.add_argument("--hf-config")
    ap.add_argument("--text-column", default="text")
    ap.add_argument("--name", help="output name for --dataset hf")
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() - 2))
    a = ap.parse_args()

    if a.dataset == "fineweb10B":
        out = os.path.join(a.out, "fineweb10B")
        os.makedirs(out, exist_ok=True)
        download_fineweb10B(out, a.train_shards)
        return
    if a.dataset == "hf":
        if not a.hf_dataset:
            ap.error("--hf-dataset is required")
        name, (ds, cfg, col) = a.name or a.hf_dataset.split("/")[-1], (a.hf_dataset, a.hf_config, a.text_column)
    else:
        name, (ds, cfg, col) = a.dataset, HF_PRESETS[a.dataset]
    out = os.path.join(a.out, name)
    os.makedirs(out, exist_ok=True)
    tokenize_hf(out, name, ds, cfg, col, a.max_tokens, a.shard_tokens, a.val_tokens, a.workers)


if __name__ == "__main__":
    main()
