"""Batched KV-cached sampling for post-training (RFT / RL rollouts / evals).

Rollouts replicate one prompt G times, so every row shares the prompt length:
no left padding, no position offsets, and exactly the group structure GRPO
needs. The loop count r and zero state-init are fixed per call so the policy
that sampled is the policy that gets updated (on-policy for looped models).
"""

from __future__ import annotations

from contextlib import nullcontext

import torch
import torch.nn.functional as F

from .chat import decode, extract_answer, render_prompt
from .config import END_TURN, GPT2_EOT


@torch.no_grad()
def sample_group(model, prompt_ids, G: int, max_new: int, *, num_steps: int,
                 temperature: float = 1.0, top_k: int | None = 50, stop=(END_TURN, GPT2_EOT)):
    """Returns a list of G completions (token lists, including the stop token
    when one was produced)."""
    was_training = model.training
    model.eval()
    dev = model.embed.weight.device
    idx = torch.tensor([prompt_ids] * G, device=dev)
    cache = model.new_cache(G, len(prompt_ids) + max_new, n_slots=num_steps)
    out = model(idx, num_steps=num_steps, cache=cache, last_only=True, init_state="zero")
    outs = [[] for _ in range(G)]
    done = torch.zeros(G, dtype=torch.bool, device=dev)
    stop_t = torch.tensor(list(stop), device=dev)
    for _ in range(max_new):
        logits = out["logits"][:, -1].float()
        if temperature <= 0:
            nxt = logits.argmax(-1)
        else:
            logits = logits / temperature
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            nxt = torch.multinomial(F.softmax(logits, dim=-1), 1).squeeze(1)
        for g in torch.nonzero(~done).flatten().tolist():
            outs[g].append(int(nxt[g]))
        done |= torch.isin(nxt, stop_t)
        if bool(done.all()):
            break
        out = model(nxt[:, None], num_steps=num_steps, cache=cache, last_only=True, init_state="zero")
    model.train(was_training)
    return outs


def completion_text(enc, tokens):
    toks = [t for t in tokens if t not in (END_TURN, GPT2_EOT)]
    return decode(enc, toks)


def gsm8k_accuracy(model, enc, examples, num_steps, device_type="cuda", max_new=256,
                   samples: int = 1, temperature: float = 0.0):
    """pass@1 (greedy, samples=1) or pass@k (any of k samples correct)."""
    amp = (torch.autocast("cuda", dtype=torch.bfloat16) if device_type == "cuda" else nullcontext())
    hits = 0
    with amp:
        for ex in examples:
            prompt = render_prompt(enc, ex["messages"][:1])
            outs = sample_group(model, prompt, samples, max_new, num_steps=num_steps,
                                temperature=temperature if samples > 1 else 0.0)
            preds = [extract_answer(completion_text(enc, o)) for o in outs]
            hits += any(p == ex["answer"] for p in preds)
    return hits / max(1, len(examples))
