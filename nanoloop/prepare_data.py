"""Download / tokenize pretraining data into uint16 shards under data/<name>/.

  # The modded-nanogpt benchmark data (pre-tokenized GPT-2 FineWeb, ~100M tok/shard).
  # Use this val set to compare against the 3.28 "GPT-2 124M" target.
  python prepare_data.py fineweb10B --train-shards 30

  # Higher-quality corpora, tokenized locally with the GPT-2 BPE:
  python prepare_data.py fineweb-edu --max-tokens 5e9
  python prepare_data.py climbmix --max-tokens 5e9
  python prepare_data.py hf --hf-dataset <id> [--hf-config <name>] --text-column text

  # Stage-A decay-phase (mid-training) ingredients:
  python prepare_data.py finemath --max-tokens 1e9
  python prepare_data.py cosmopedia-v2 --max-tokens 5e8
  python prepare_data.py chat-mix        # smol-smoltalk + GSM8k-Aug + MMLU-aux in the chat template

  # Long-context stage ingredients (docs/RESEARCH.md §10):
  python prepare_data.py pg19 --max-tokens 3e8                          # public-domain books (~70K tok each)
  python prepare_data.py fineweb-edu --min-doc-tokens 4096 --max-tokens 1e8   # -> data/fineweb-edu-long
  python prepare_data.py synth-retrieval --max-tokens 3e7               # needle / key-value retrieval
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
    "finemath": ("HuggingFaceTB/finemath", "finemath-4plus", "text"),
    "cosmopedia-v2": ("HuggingFaceTB/smollm-corpus", "cosmopedia-v2", "text"),
    "pg19": ("fla-hub/pg19", None, "text"),  # parquet copy of DeepMind PG-19 (check the column name)
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
                max_tokens: float, shard_tokens: int, val_tokens: int, workers: int,
                min_doc_tokens: int = 0) -> None:
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
            if len(toks) < min_doc_tokens:  # long-context data: keep only long documents
                continue
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


def write_chat_mix(out_dir: str, spec: str, shard_tokens: int, val_tokens: int) -> None:
    """Render chat/instruction data with the chat template into token shards, so
    the decay phase teaches the format (nanochat-style midtraining). Plain LM
    loss on every token; sft.py later masks to assistant turns only."""
    import random

    import tiktoken

    from nanoloop.chat import build_mixture, render_conversation

    enc = tiktoken.get_encoding("gpt2")
    convs = build_mixture(spec, seed=0)
    random.Random(0).shuffle(convs)
    toks = np.concatenate([np.asarray(render_conversation(enc, c["messages"])[0], dtype=np.uint16)
                           for c in convs])
    write_shard(os.path.join(out_dir, "chat-mix_val_000000.bin"), toks[:val_tokens])
    rest = toks[val_tokens:]
    for i in range(0, len(rest), shard_tokens):
        write_shard(os.path.join(out_dir, f"chat-mix_train_{i // shard_tokens + 1:06d}.bin"),
                    rest[i:i + shard_tokens])
    print(f"chat-mix: {len(convs):,} conversations, {len(toks):,} tokens")


def write_synth_retrieval(out_dir, haystack, max_tokens, shard_tokens, max_len):
    import glob

    import tiktoken

    from nanoloop.data import load_shard
    from nanoloop.longctx import synth_retrieval_stream

    files = sorted(glob.glob(haystack))
    if not files:
        raise SystemExit(f"no haystack shards match {haystack!r}; prepare fineweb-edu first")
    hay = np.asarray(load_shard(files[0]))
    lengths = tuple(L for L in (1024, 2048, 4096, 8192, 16384, 32768) if L <= max_len)
    gen = synth_retrieval_stream(tiktoken.get_encoding("gpt2"), hay, lengths)
    shard, total = 0, 0
    while total < max_tokens:
        target = 1_000_000 if shard == 0 else shard_tokens
        buf = []
        while len(buf) < target and total + len(buf) < max_tokens:
            buf += next(gen)
        split = "val" if shard == 0 else "train"
        write_shard(os.path.join(out_dir, f"synth-retrieval_{split}_{shard:06d}.bin"), buf)
        total += len(buf)
        shard += 1
    print(f"synth-retrieval: {total:,} tokens in {shard} shards")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", choices=["fineweb10B", "hf", "chat-mix", "synth-retrieval", *HF_PRESETS])
    ap.add_argument("--min-doc-tokens", type=int, default=0,
                    help="keep only documents at least this long (writes <name>-long)")
    ap.add_argument("--haystack", default="data/fineweb-edu/*_train_*.bin",
                    help="synth-retrieval: token shards used as filler text")
    ap.add_argument("--max-len", type=int, default=16384, help="synth-retrieval: longest sequence")
    ap.add_argument("--chat-spec", default="smoltalk:1,gsm8k-aug:0.5,mmlu:1",
                    help="chat-mix sources (source:epochs)")
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
    if a.dataset == "synth-retrieval":
        out = os.path.join(a.out, "synth-retrieval")
        os.makedirs(out, exist_ok=True)
        write_synth_retrieval(out, a.haystack, a.max_tokens, a.shard_tokens, a.max_len)
        return
    if a.dataset == "chat-mix":
        out = os.path.join(a.out, "chat-mix")
        os.makedirs(out, exist_ok=True)
        write_chat_mix(out, a.chat_spec, a.shard_tokens, min(a.val_tokens, 2_000_000))
        return
    if a.dataset == "hf":
        if not a.hf_dataset:
            ap.error("--hf-dataset is required")
        name, (ds, cfg, col) = a.name or a.hf_dataset.split("/")[-1], (a.hf_dataset, a.hf_config, a.text_column)
    else:
        name, (ds, cfg, col) = a.dataset, HF_PRESETS[a.dataset]
    if a.min_doc_tokens:
        name += "-long"
    out = os.path.join(a.out, name)
    os.makedirs(out, exist_ok=True)
    tokenize_hf(out, name, ds, cfg, col, a.max_tokens, a.shard_tokens, a.val_tokens, a.workers,
                a.min_doc_tokens)


if __name__ == "__main__":
    main()
