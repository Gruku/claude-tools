"""Stage 2: latent ("neuralese") reasoning finetune on GSM8k-Aug.

Coconut (arXiv 2412.06769) curriculum: stage 0 is plain chain-of-thought SFT;
at stage k the first k reasoning steps are replaced by k*c continuous thoughts
-- the model's own last hidden state fed back as the next input embedding --
until, after the last stage, all language reasoning is removed. On top of that
we add the CODI (arXiv 2502.21074) self-distillation term: the same model run
on the full CoT is the teacher, and the student's hidden state at the answer
anchor is pulled toward the teacher's (L1 / teacher std). CODI reached 43.7%
on GSM8K with GPT-2 vs Coconut's 34.1%.

The recurrent core adds a second, orthogonal "thinking" axis: loops per token
(depth) x continuous thoughts (length). Evaluate the grid with --eval-steps.

  python coconut.py --init runs/<run>/ckpt_final.pt --out-dir runs/coconut
  python coconut.py --eval-only runs/coconut/stage3.pt --eval-steps 2,4,8
"""

from __future__ import annotations

import argparse
import math
import os
import random
import re
import time
from contextlib import nullcontext

import torch
import torch.nn as nn
import torch.nn.functional as F

from nanoloop.checkpoint import gpt2_tokenizer, load_model
from nanoloop.config import END_LATENT, GPT2_EOT, LATENT, START_LATENT
from nanoloop.layers import rms_norm


class LatentProjector(nn.Module):
    """h -> h + MLP(h), zero-initialised so it starts as Coconut's identity
    feedback; gives the model room to map output space back to input space
    (CODI uses a similar projection)."""

    def __init__(self, d):
        super().__init__()
        self.fc = nn.Linear(d, d, bias=False)
        self.out = nn.Linear(d, d, bias=False)
        nn.init.zeros_(self.out.weight)

    def forward(self, h):
        return rms_norm(h + self.out(F.gelu(self.fc(h))))


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------


def load_gsm8k_aug(split):
    from datasets import load_dataset

    ds = load_dataset("whynlp/gsm8k-aug", split=split)
    out = []
    for row in ds:
        steps = row.get("steps")
        if steps is None:  # CODI/iCoT format: "<<a*b=c>> <<c+d=e>>"
            cot = row.get("cot") or row.get("rationale") or ""
            steps = re.findall(r"<<[^>]*>>", cot) or [s for s in cot.split("\n") if s.strip()]
        out.append(dict(question=row["question"].strip(), steps=[s.strip() for s in steps],
                        answer=str(row["answer"]).strip().replace(",", "")))
    return out


class Formatter:
    def __init__(self, enc, c_thought, max_stage):
        self.enc, self.c, self.max_stage = enc, c_thought, max_stage
        self.hash = enc.encode("###")

    def n_latent(self, stage):
        return min(stage, self.max_stage) * self.c

    def build(self, ex, stage, with_answer=True):
        """Returns ids, labels, latent positions, answer-anchor position."""
        enc = self.enc
        q = [GPT2_EOT] + enc.encode(ex["question"] + "\n")
        steps = [enc.encode(s + "\n") for s in ex["steps"]]
        ans = enc.encode(" " + ex["answer"]) + [GPT2_EOT] if with_answer else []
        if stage == 0:
            pre, lat_pos = q, []
            rest = [t for s in steps for t in s]
        else:
            n = self.n_latent(stage)
            pre = q + [START_LATENT] + [LATENT] * n + [END_LATENT]
            lat_pos = list(range(len(q) + 1, len(q) + 1 + n))
            keep = steps[stage:] if stage < self.max_stage else []
            rest = [t for s in keep for t in s]
        ids = pre + rest + self.hash + ans
        labels = [-1] * len(pre) + rest + self.hash + ans
        anchor = len(pre) + len(rest) + len(self.hash) - 1  # predicts the answer
        return ids, labels, lat_pos, anchor


def collate(items, device):
    T = max(len(i[0]) for i in items)
    ids = torch.full((len(items), T), GPT2_EOT, dtype=torch.long)
    lab = torch.full((len(items), T), -1, dtype=torch.long)
    for b, (i, l, _, _) in enumerate(items):
        ids[b, :len(i)] = torch.tensor(i)
        lab[b, :len(l)] = torch.tensor(l)
    lat = torch.tensor([i[2] for i in items], dtype=torch.long)  # [B, n_lat]
    anchor = torch.tensor([i[3] for i in items], dtype=torch.long)
    # next-token targets: position t predicts labels[t+1]
    tgt = torch.cat([lab[:, 1:], torch.full((len(items), 1), -1)], dim=1)
    return ids.to(device), tgt.to(device), lat.to(device), anchor.to(device)


# ----------------------------------------------------------------------------
# Latent forward
# ----------------------------------------------------------------------------


def latent_forward(model, proj, ids, lat, steps, targets=None):
    """Fill each latent slot sequentially with the projected hidden state of the
    preceding position, then run the final pass. Gradients flow through the
    whole chain of thoughts (as in Coconut)."""
    B = ids.size(0)
    d = model.cfg.d_model
    emb = torch.zeros(B, ids.size(1), d, device=ids.device)
    mask = torch.zeros_like(ids, dtype=torch.bool)
    rows = torch.arange(B, device=ids.device)
    for j in range(lat.size(1)):
        pos = lat[:, j]
        upto = int(pos.max().item())  # only the prefix is needed for this thought
        h = model(ids[:, :upto], num_steps=steps, embed_override=emb[:, :upto],
                  override_mask=mask[:, :upto], return_hidden=True)["hidden"]
        thought = proj(h[rows, pos - 1].float())
        emb = emb.clone()
        emb[rows, pos] = thought
        mask = mask.clone()
        mask[rows, pos] = True
    return model(ids, targets, num_steps=steps, embed_override=emb if lat.numel() else None,
                 override_mask=mask if lat.numel() else None, return_hidden=True)


# ----------------------------------------------------------------------------
# Evaluation (KV-cached latent decoding)
# ----------------------------------------------------------------------------


@torch.no_grad()
def solve(model, proj, fmt, ex, stage, steps, max_new=128):
    ids, _, lat_pos, _ = fmt.build(ex, stage, with_answer=False)
    dev = model.embed.weight.device
    if stage == 0:
        prompt = ids[: len(ids) - len(fmt.hash)]  # question only; model writes CoT
    else:
        prompt = ids[: lat_pos[0]] if lat_pos else ids
    cache = model.new_cache(1, len(ids) + max_new + 8, n_slots=steps)
    out = model(torch.tensor([prompt], device=dev), num_steps=steps, cache=cache, return_hidden=True)
    if stage > 0:
        for _ in lat_pos:  # continuous thoughts
            thought = proj(out["hidden"][:, -1].float())
            out = model(torch.tensor([[LATENT]], device=dev), num_steps=steps, cache=cache,
                        embed_override=thought[:, None], return_hidden=True,
                        override_mask=torch.ones(1, 1, dtype=torch.bool, device=dev))
        out = model(torch.tensor([[END_LATENT]], device=dev), num_steps=steps, cache=cache,
                    return_hidden=True)
    gen = []
    for _ in range(max_new):
        nxt = int(out["logits"][0, -1].argmax())
        if nxt == GPT2_EOT:
            break
        gen.append(nxt)
        out = model(torch.tensor([[nxt]], device=dev), num_steps=steps, cache=cache)
    text = fmt.enc.decode([t for t in gen if t < fmt.enc.n_vocab])
    pred = text.split("###")[-1].strip().replace(",", "")
    return pred, text


def evaluate(model, proj, fmt, data, stage, steps, amp):
    model.eval()
    correct = 0
    with amp:
        for ex in data:
            pred, _ = solve(model, proj, fmt, ex, stage, steps)
            correct += pred == ex["answer"]
    model.train()
    return correct / max(1, len(data))


# ----------------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", help="pretrained checkpoint from train.py")
    ap.add_argument("--eval-only", help="evaluate a coconut.py checkpoint")
    ap.add_argument("--out-dir", default="runs/coconut")
    ap.add_argument("--cot-epochs", type=int, default=6, help="stage 0: plain CoT SFT")
    ap.add_argument("--stage-epochs", type=int, default=3)
    ap.add_argument("--max-stage", type=int, default=3)
    ap.add_argument("--c-thought", type=int, default=2, help="continuous thoughts per removed step")
    ap.add_argument("--distill-weight", type=float, default=1.0, help="CODI teacher CE + L1 (0 = pure Coconut)")
    ap.add_argument("--steps", type=int, default=4, help="recurrent loops per token during finetune")
    ap.add_argument("--eval-steps", default=None, help="comma list of loop counts for final eval")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--eval-limit", type=int, default=300)
    ap.add_argument("--train-limit", type=int, default=None)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    random.seed(a.seed)
    torch.manual_seed(a.seed)
    is_cuda = a.device.startswith("cuda")
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if is_cuda else nullcontext()
    enc = gpt2_tokenizer()
    fmt = Formatter(enc, a.c_thought, a.max_stage)
    test = load_gsm8k_aug("test")

    if a.eval_only:
        ck = torch.load(a.eval_only, map_location=a.device, weights_only=False)
        model = load_model(a.eval_only, a.device)
        proj = LatentProjector(model.cfg.d_model).to(a.device)
        proj.load_state_dict(ck["proj"])
        for r in ([int(s) for s in a.eval_steps.split(",")] if a.eval_steps else [a.steps]):
            acc = evaluate(model, proj, fmt, test[: a.eval_limit], ck["stage"], r, amp)
            print(f"stage {ck['stage']} loops={r}: GSM8K acc {acc * 100:.2f}%")
        return

    model = load_model(a.init, a.device)
    model.train()
    proj = LatentProjector(model.cfg.d_model).to(a.device)
    train = load_gsm8k_aug("train")[: a.train_limit]
    os.makedirs(a.out_dir, exist_ok=True)

    schedule = [0] * a.cot_epochs + [s for s in range(1, a.max_stage + 1) for _ in range(a.stage_epochs)]
    prev_stage = None
    for epoch, stage in enumerate(schedule):
        if stage != prev_stage:  # Coconut resets the optimizer every stage
            params = list(model.parameters()) + list(proj.parameters())
            opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=a.weight_decay, betas=(0.9, 0.95))
            prev_stage = stage
        random.shuffle(train)
        n_batches = math.ceil(len(train) / a.batch_size)
        t0 = time.time()
        for bi in range(n_batches):
            batch = train[bi * a.batch_size:(bi + 1) * a.batch_size]
            ids, tgt, lat, anchor = collate([fmt.build(ex, stage) for ex in batch], a.device)
            with amp:
                out = latent_forward(model, proj, ids, lat, a.steps, tgt)
                loss = out["loss"]
                if stage > 0 and a.distill_weight > 0:
                    t_ids, t_tgt, _, t_anchor = collate([fmt.build(ex, 0) for ex in batch], a.device)
                    t_out = model(t_ids, t_tgt, num_steps=a.steps, return_hidden=True)
                    rows = torch.arange(ids.size(0), device=ids.device)
                    h_t = t_out["hidden"][rows, t_anchor].float().detach()
                    h_s = out["hidden"][rows, anchor].float()
                    distill = (h_s - h_t).abs().mean() / h_t.std().clamp(min=1e-6)
                    loss = loss + a.distill_weight * (t_out["loss"] + distill)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 2.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
            if bi % 50 == 0:
                print(f"epoch {epoch} stage {stage} batch {bi}/{n_batches} loss {loss.item():.4f} "
                      f"({time.time() - t0:.0f}s)", flush=True)
        acc = evaluate(model, proj, fmt, test[: a.eval_limit], stage, a.steps, amp)
        print(f"== epoch {epoch} stage {stage}: GSM8K acc {acc * 100:.2f}% (n={min(a.eval_limit, len(test))})",
              flush=True)
        if epoch == len(schedule) - 1 or schedule[epoch + 1] != stage:
            path = os.path.join(a.out_dir, f"stage{stage}.pt")
            torch.save(dict(model=model.state_dict(), proj=proj.state_dict(), stage=stage,
                            config=model.cfg.to_dict()), path)
            print(f"saved {path}")


if __name__ == "__main__":
    main()
