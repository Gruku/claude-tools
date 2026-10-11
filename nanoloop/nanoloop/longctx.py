"""Synthetic long-context retrieval data and needle-in-a-haystack (NIAH) probes.

Small models learn long-range retrieval last. A few percent of synthetic
retrieval sequences in the long-context stage teaches retrieval heads cheaply,
and gains transfer to real long-context tasks (arXiv 2406.19292). The same
generator, with held-out haystacks and words, drives eval_niah.py.

Formats (plain text inside real web-text haystacks):
  needle   "The special magic number for <word> is <7 digits>."  (1-4 needles, 1 queried)
  kv       a list of "<key>: <value>" lines with a lookup question at the end
"""

from __future__ import annotations

import random

import numpy as np

from .config import GPT2_EOT

WORDS = ("apple river castle violet engine harbor meadow lantern copper falcon glacier orchard "
         "pepper quartz saddle thunder velvet willow anchor basil cedar dolphin ember feather "
         "garnet hollow island jasmine kettle lemon marble nectar oyster pebble quiver raven "
         "sapphire tulip umbrella vapor walnut yarrow zephyr bramble canyon drizzle ferry grove").split()
HELD_OUT = ("cobalt lilac mango nimbus onyx prairie quince rustic sequoia tundra").split()


def _needle(word, num):
    return f" The special magic number for {word} is {num}."


def _question(word):
    return f"\nQuestion: What is the special magic number for {word}?\nAnswer: The special magic number for {word} is"


def _haystack(rng, hay: np.ndarray, n: int):
    start = rng.randrange(0, max(1, len(hay) - n - 1))
    toks = [int(t) for t in hay[start:start + n]]
    return [t for t in toks if t != GPT2_EOT]  # one continuous "document"


def needle_example(rng, enc, hay, length, depth=None, n_needles=None, words=WORDS, with_answer=True):
    """Returns (tokens, answer_str). Total length ~= `length` tokens; the
    queried needle sits at relative `depth` in [0, 1] (random if None)."""
    n_needles = n_needles or rng.randint(1, 4)
    keys = rng.sample(words, n_needles)
    nums = [str(rng.randint(1_000_000, 9_999_999)) for _ in keys]
    target = rng.randrange(n_needles)
    needles = [enc.encode_ordinary(_needle(k, v)) for k, v in zip(keys, nums)]
    q = enc.encode_ordinary(_question(keys[target]))
    ans = enc.encode_ordinary(" " + nums[target] + ".")
    budget = length - sum(map(len, needles)) - len(q) - (len(ans) if with_answer else 0) - 1
    body = _haystack(rng, hay, max(16, budget))
    depths = [rng.random() for _ in needles]
    if depth is not None:
        depths[target] = depth
    for d, nd in sorted(zip(depths, needles), key=lambda x: -x[0]):  # insert back to front
        pos = int(d * len(body))
        body = body[:pos] + nd + body[pos:]
    toks = [GPT2_EOT] + body + q + (ans if with_answer else [])
    return toks, nums[target]


def kv_example(rng, enc, length, with_answer=True):
    """A long list of random key: value pairs, then a lookup."""
    pairs, toks = [], []
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    lines = []
    while True:
        k = "".join(rng.choices(alphabet, k=6))
        v = "".join(rng.choices(alphabet, k=6))
        line = enc.encode_ordinary(f"{k}: {v}\n")
        if len(toks) + len(line) > length - 40:
            break
        toks += line
        pairs.append((k, v))
    k, v = rng.choice(pairs)
    q = enc.encode_ordinary(f"\nLookup {k}. Value: ")
    ans = enc.encode_ordinary(v)
    return [GPT2_EOT] + enc.encode_ordinary("Key-value store:\n") + toks + q + (ans if with_answer else []), v


def synth_retrieval_stream(enc, hay, lengths=(1024, 2048, 4096, 8192, 16384), kv_frac=0.25, seed=0):
    """Endless generator of training sequences (token lists)."""
    rng = random.Random(seed)
    while True:
        L = rng.choice(lengths)
        if rng.random() < kv_frac:
            yield kv_example(rng, enc, L)[0]
        else:
            yield needle_example(rng, enc, hay, L)[0]
