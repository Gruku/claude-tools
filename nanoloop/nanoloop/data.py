"""Token shards in the llm.c / modded-nanogpt format (256 x int32 header, then
uint16 tokens), so pre-tokenized FineWeb shards can be used as-is."""

from __future__ import annotations

import glob
import os

import numpy as np
import torch

MAGIC, VERSION, HEADER_INTS = 20240520, 1, 256


def write_shard(path: str, tokens) -> None:
    tokens = np.asarray(tokens, dtype=np.uint16)
    header = np.zeros(HEADER_INTS, dtype=np.int32)
    header[0], header[1], header[2] = MAGIC, VERSION, len(tokens)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(header.tobytes())
        f.write(tokens.tobytes())
    os.replace(tmp, path)


def load_shard(path: str) -> np.ndarray:
    header = np.fromfile(path, dtype=np.int32, count=HEADER_INTS)
    if header[0] != MAGIC:
        raise ValueError(f"{path}: bad magic {header[0]}")
    n = int(header[2])
    return np.memmap(path, dtype=np.uint16, mode="r", offset=HEADER_INTS * 4, shape=(n,))


class TokenLoader:
    """Streams contiguous [B, T+1] windows through the shards; each rank reads a
    disjoint stride. Resumable via state_dict()."""

    def __init__(self, pattern: str, B: int, T: int, rank: int = 0, world: int = 1):
        self.files = sorted(glob.glob(pattern))
        if not self.files:
            raise FileNotFoundError(f"no shards match {pattern!r} (run prepare_data.py)")
        self.B, self.T, self.rank, self.world = B, T, rank, world
        self.shard_idx, self.pos = 0, 0
        self.epoch = 0
        self._tokens = load_shard(self.files[0])

    def _advance_shard(self):
        self.shard_idx += 1
        if self.shard_idx >= len(self.files):
            self.shard_idx, self.epoch = 0, self.epoch + 1
        self._tokens = load_shard(self.files[self.shard_idx])
        self.pos = 0

    def next_batch(self, device="cpu"):
        span = self.B * self.T
        while self.pos + span * self.world + 1 > len(self._tokens):
            self._advance_shard()
        start = self.pos + self.rank * span
        buf = torch.from_numpy(self._tokens[start:start + span + 1].astype(np.int64))
        self.pos += span * self.world
        x = buf[:-1].view(self.B, self.T)
        y = buf[1:].view(self.B, self.T)
        if str(device).startswith("cuda"):
            return x.pin_memory().to(device, non_blocking=True), y.pin_memory().to(device, non_blocking=True)
        return x.to(device), y.to(device)

    def state_dict(self):
        return dict(shard_idx=self.shard_idx, pos=self.pos, epoch=self.epoch)

    def load_state_dict(self, st):
        self.shard_idx, self.pos, self.epoch = st["shard_idx"], st["pos"], st["epoch"]
        self._tokens = load_shard(self.files[self.shard_idx])
