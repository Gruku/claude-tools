"""Stage F (frontier): LOTUS-style parallel latent reasoning (arXiv 2606.31779).

Coconut/CODI generate continuous thoughts one after another (n+1 sequential
passes, each costing r loops in a looped model) and supervise them only
weakly, which 2026 work shows invites shortcuts and latent collapse
(2602.22441, 2606.20075). LOTUS instead lays out a fixed workspace of K blocks
x c latent slots, lets the *looped* backbone refine all slots in parallel, and
supervises every slot with its own token of the gold reasoning step:

    <|user|> Q <|end|><|assistant|> <|start-latent|> [Z_1,1..c] .. [Z_K,1..c] <|end-latent|> #### A <|end|>

    slot (k, j) input  = learned base + block_pos[k] + slot_pos[j]   (no hidden-state feedback)
    slot (k, j) target = j-th token of step k, or <|pad-step|> past its end
    loss = CE(answer) + lat_weight * mean CE(slots) [+ deep_weight * per-loop slot CE]
           [+ codi_weight * L1(answer-anchor hidden, CoT teacher)]

NanoLoop's recurrent core *is* LOTUS's weight-shared refinement loop R, so this
costs one forward pass per example (vs n+1 for Coconut). LOTUS reports GPT-2
44.1% on GSM8K (CoT 42.7) and is the first latent method whose gap to CoT does
not grow with scale (3B: 70.0 vs 71.5).

Decoding the slots through the LM head gives a readable thought trace.
Evaluation follows the critiques: accuracy vs loop count, and with zero slots
(a shortcut test: a model that still answers well without its workspace isn't
using it).

  python lotus.py --init runs/sft-math/ckpt_final.pt --out-dir runs/lotus
  python lotus.py --eval-only runs/lotus/ckpt_final.pt --eval-steps 2,4,6,8,12 --show 3
"""

from __future__ import annotations

import argparse
import math
import os
import random
import time
from contextlib import nullcontext

import torch
import torch.nn as nn
import torch.nn.functional as F

from nanoloop.chat import decode, extract_answer, normalize_number
from nanoloop.checkpoint import gpt2_tokenizer, load_checkpoint
from nanoloop.config import (ASSISTANT, END_LATENT, END_TURN, GPT2_EOT, LATENT, PAD_STEP,
                             START_LATENT, USER)
from nanoloop.gsm8k_aug import load_gsm8k_aug


class LatentSlots(nn.Module):
    """Input embeddings for the K x c latent workspace."""

    def __init__(self, d, K, c):
        super().__init__()
        self.K, self.c = K, c
        self.base = nn.Parameter(torch.randn(d) * 0.02)
        self.block_pos = nn.Parameter(torch.randn(K, d) * 0.02)
        self.slot_pos = nn.Parameter(torch.randn(c, d) * 0.02)

    def forward(self, n_blocks=None):
        K = self.K if n_blocks is None else n_blocks
        if K == 0:
            return self.base.new_zeros(0, self.base.numel())
        e = self.base + self.block_pos[:K, None, :] + self.slot_pos[None, :, :]
        return e.reshape(K * self.c, -1)  # [K*c, d]


class Formatter:
    def __init__(self, enc, K, c):
        self.enc, self.K, self.c = enc, K, c
        self.hash = enc.encode_ordinary("####")

    def prompt(self, ex):
        return [GPT2_EOT, USER] + self.enc.encode_ordinary(ex["question"]) + [END_TURN, ASSISTANT]

    def step_targets(self, ex):
        steps = [self.enc.encode_ordinary(s) for s in ex["steps"]]
        if len(steps) > self.K:  # overflow folds into the last block (truncated to c)
            steps = steps[:self.K - 1] + [sum(steps[self.K - 1:], [])]
        steps += [[]] * (self.K - len(steps))
        return [(s + [PAD_STEP] * self.c)[:self.c] for s in steps]

    def build(self, ex, n_blocks=None, with_answer=True):
        """ids, targets (aligned: targets[t] is what position t must predict), slot span."""
        K = self.K if n_blocks is None else n_blocks
        q = self.prompt(ex)
        slots = [LATENT] * (K * self.c)
        ans = self.enc.encode_ordinary(" " + ex["answer"]) + [END_TURN] if with_answer else []
        ids = q + [START_LATENT] + slots + [END_LATENT] + self.hash + ans
        tgt = [-1] * len(ids)
        s0 = len(q) + 1
        for k, step in enumerate(self.step_targets(ex)[:K]):
            for j, t in enumerate(step):
                tgt[s0 + k * self.c + j] = t  # each slot reads out its own content
        e = s0 + K * self.c  # <|end-latent|> position: from here on, ordinary next-token
        for t in range(e, len(ids) - 1):
            tgt[t] = ids[t + 1]
        return ids, tgt, (s0, e)


def collate(items, device):
    T = max(len(i[0]) for i in items)
    ids = torch.full((len(items), T), GPT2_EOT, dtype=torch.long)
    tgt = torch.full((len(items), T), -1, dtype=torch.long)
    for b, (i, t, _) in enumerate(items):
        ids[b, :len(i)] = torch.tensor(i)
        tgt[b, :len(t)] = torch.tensor(t)
    spans = torch.tensor([it[2] for it in items])
    return ids.to(device), tgt.to(device), spans.to(device)


def slot_override(slots_mod, ids, spans, n_blocks=None):
    """Embedding overrides placing the workspace embeddings at each row's slots."""
    B, T = ids.shape
    lat = slots_mod(n_blocks)  # [K*c, d]
    emb = torch.zeros(B, T, lat.size(-1), device=ids.device, dtype=lat.dtype)
    mask = torch.zeros(B, T, dtype=torch.bool, device=ids.device)
    for b in range(B):
        s, e = spans[b].tolist()
        emb[b, s:e] = lat[: e - s]
        mask[b, s:e] = True
    return emb, mask


def lotus_loss(model, slots_mod, ids, tgt, spans, steps, lat_weight=1.0, deep_weight=0.0):
    emb, mask = slot_override(slots_mod, ids, spans)
    out = model(ids, num_steps=steps, embed_override=emb, override_mask=mask, return_hidden=True,
                last_only=True, loop_readout=deep_weight > 0)
    slot_t = torch.where(mask, tgt, torch.full_like(tgt, -1))
    ans_t = torch.where(mask, torch.full_like(tgt, -1), tgt)
    l_ans = model.lm_loss(out["hidden"], ans_t)
    l_lat = model.lm_loss(out["hidden"], slot_t)
    loss = l_ans + lat_weight * l_lat
    if deep_weight > 0 and len(out["loop_hidden"]) > 1:
        n = len(out["loop_hidden"]) - 1
        deep = sum((i + 1) / n * model.lm_loss(h, slot_t) for i, h in enumerate(out["loop_hidden"][:-1])) / n
        loss = loss + deep_weight * deep
    return loss, l_ans.detach(), l_lat.detach(), out


@torch.no_grad()
def solve(model, slots_mod, fmt, ex, steps, n_blocks=None, max_new=24):
    """Prefill question + whole workspace in ONE pass, then decode the answer."""
    model.eval()
    dev = model.embed.weight.device
    ids, _, span = fmt.build(ex, n_blocks, with_answer=False)
    x = torch.tensor([ids], device=dev)
    emb, mask = slot_override(slots_mod, x, torch.tensor([span]), n_blocks)
    cache = model.new_cache(1, len(ids) + max_new + 4, n_slots=steps)
    out = model(x, num_steps=steps, cache=cache, embed_override=emb, override_mask=mask,
                return_hidden=True, init_state="zero")
    s, e = span
    trace_ids = out["logits"][0, s:e].argmax(-1).view(-1, fmt.c).tolist() if e > s else []
    trace = [decode(fmt.enc, [t for t in blk if t != PAD_STEP]) for blk in trace_ids]
    gen = []
    nxt = int(out["logits"][0, -1].argmax())
    for _ in range(max_new):
        if nxt in (END_TURN, GPT2_EOT):
            break
        gen.append(nxt)
        out = model(torch.tensor([[nxt]], device=dev), num_steps=steps, cache=cache, init_state="zero")
        nxt = int(out["logits"][0, -1].argmax())
    text = "####" + decode(fmt.enc, gen)
    return extract_answer(text), trace


def evaluate(model, slots_mod, fmt, data, steps, amp, n_blocks=None, show=0):
    correct = 0
    with amp:
        for i, ex in enumerate(data):
            pred, trace = solve(model, slots_mod, fmt, ex, steps, n_blocks)
            correct += pred == normalize_number(ex["answer"])
            if i < show:
                print(f"Q: {ex['question'][:100]}\n  thoughts: {[t for t in trace if t]}\n"
                      f"  pred={pred} gold={ex['answer']}")
    return correct / max(1, len(data))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", help="task-SFT (stage C) or pretrained checkpoint")
    ap.add_argument("--eval-only", help="a lotus.py checkpoint")
    ap.add_argument("--out-dir", default="runs/lotus")
    ap.add_argument("--K", type=int, default=6, help="latent blocks (one per reasoning step)")
    ap.add_argument("--c", type=int, default=13, help="slots per block (LOTUS GPT-2 setting)")
    ap.add_argument("--epochs", type=float, default=8)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--accum", type=int, default=4, help="effective batch = batch_size * accum")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--lat-weight", type=float, default=1.0)
    ap.add_argument("--deep-weight", type=float, default=0.3, help="per-loop slot supervision")
    ap.add_argument("--steps", type=int, default=None, help="fixed loops (default: sample as in pretraining)")
    ap.add_argument("--eval-steps", default=None)
    ap.add_argument("--eval-limit", type=int, default=300)
    ap.add_argument("--eval-every", type=int, default=1000)
    ap.add_argument("--show", type=int, default=0, help="print N thought traces at eval")
    ap.add_argument("--train-limit", type=int, default=None)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    random.seed(a.seed)
    torch.manual_seed(a.seed)
    is_cuda = a.device.startswith("cuda")
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if is_cuda else nullcontext()
    enc = gpt2_tokenizer()
    test = load_gsm8k_aug("test")[: a.eval_limit]

    if a.eval_only:
        model, ck = load_checkpoint(a.eval_only, a.device)
        K, c = ck["K"], ck["c"]
        fmt = Formatter(enc, K, c)
        slots = LatentSlots(model.cfg.d_model, K, c).to(a.device)
        slots.load_state_dict(ck["slots"])
        rs = [int(r) for r in a.eval_steps.split(",")] if a.eval_steps else [model.cfg.mean_recurrence]
        for r in rs:
            acc = evaluate(model, slots, fmt, test, r, amp, show=a.show)
            print(f"GSM8K (LOTUS) @ loops={r}: {acc * 100:.2f}%")
        r0 = model.cfg.mean_recurrence
        print(f"shortcut test, zero latent blocks @ loops={r0}: "
              f"{evaluate(model, slots, fmt, test, r0, amp, n_blocks=0) * 100:.2f}% "
              "(should be far below the full-workspace score)")
        return

    model, ck = load_checkpoint(a.init, a.device)
    if not ck.get("chat_init"):
        from sft import init_special_tokens
        init_special_tokens(model)
    model.train()
    fmt = Formatter(enc, a.K, a.c)
    slots = LatentSlots(model.cfg.d_model, a.K, a.c).to(a.device)
    train = load_gsm8k_aug("train")[: a.train_limit]
    params = list(model.parameters()) + list(slots.parameters())
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=a.weight_decay, betas=(0.9, 0.95))
    n_steps = int(math.ceil(len(train) / (a.batch_size * a.accum)) * a.epochs)
    os.makedirs(a.out_dir, exist_ok=True)
    print(f"{len(train):,} examples, {n_steps} optimizer steps, workspace {a.K}x{a.c} slots")

    t0, order, cursor = time.time(), list(range(len(train))), len(train)
    for step in range(n_steps):
        lr = a.lr * 0.5 * (1 + math.cos(math.pi * step / n_steps)) * min(1.0, (step + 1) / 100)
        for g in opt.param_groups:
            g["lr"] = lr
        tot = la = ll = 0.0
        for _ in range(a.accum):
            if cursor + a.batch_size > len(order):
                random.shuffle(order)
                cursor = 0
            batch = [train[i] for i in order[cursor:cursor + a.batch_size]]
            cursor += a.batch_size
            ids, tgt, spans = collate([fmt.build(ex) for ex in batch], a.device)
            r = a.steps or model.sample_num_steps()
            with amp:
                loss, l_ans, l_lat, _ = lotus_loss(model, slots, ids, tgt, spans, r,
                                                   a.lat_weight, a.deep_weight)
            (loss / a.accum).backward()
            tot, la, ll = tot + loss.item() / a.accum, la + l_ans.item() / a.accum, ll + l_lat.item() / a.accum
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        if step % 20 == 0:
            print(f"step {step}/{n_steps} loss {tot:.4f} (answer {la:.4f}, slots {ll:.4f}) "
                  f"lr {lr:.2e} {time.time() - t0:.0f}s", flush=True)
        if (step + 1) % a.eval_every == 0 or step == n_steps - 1:
            acc = evaluate(model, slots, fmt, test, model.cfg.mean_recurrence, amp, show=a.show)
            model.train()
            print(f"== step {step + 1}: GSM8K {acc * 100:.2f}% (n={len(test)})", flush=True)
            torch.save(dict(model=model.state_dict(), slots=slots.state_dict(), K=a.K, c=a.c,
                            config=model.cfg.to_dict(), chat_init=True, stage="lotus"),
                       os.path.join(a.out_dir, "ckpt_final.pt"))


if __name__ == "__main__":
    main()
