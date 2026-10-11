"""Reinforcement learning with verifiable rewards on GSM8K (stages D and E).

  # D: online rejection-sampling finetuning / expert iteration (positive-only)
  python rl.py --init runs/sft-math/ckpt_final.pt --algo rft --out-dir runs/rft
  # E: Dr. GRPO (no std / length normalisation, no KL, no reference model)
  python rl.py --init runs/rft/ckpt_final.pt --algo drgrpo --out-dir runs/grpo
  # E': + per-loop credit (RLTT, arXiv 2602.10520): the same advantage is applied
  #     to the read-out of every back-propagated loop, not just the last one
  python rl.py --init ... --algo drgrpo --loop-credit all

RL only sharpens what the model can already sample: it hurts tiny base models
(TinyZero, L20-Edu-135M). The script measures pass@G on training prompts first
and refuses to start below --min-passk unless --force.

On-policy for a looped model means the rollout and the update use the same loop
count r and the same (zero) initial state; r is resampled every step from the
pretraining distribution so depth scaling is preserved.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from contextlib import nullcontext

import torch

from nanoloop.chat import extract_answer, load_source, render_prompt
from nanoloop.checkpoint import gpt2_tokenizer, load_checkpoint, save_checkpoint
from nanoloop.config import GPT2_EOT
from nanoloop.engine import completion_text, gsm8k_accuracy, sample_group
from nanoloop.optim import build_optimizers


def rollouts(model, enc, batch, a, r, amp):
    """Returns list of (prompt_ids, completion_ids, advantage) and stats."""
    seqs, rewards, signal = [], [], 0
    with amp:
        for ex in batch:
            prompt = render_prompt(enc, ex["messages"][:1])
            outs, forced = sample_group(model, prompt, a.G, a.max_new, num_steps=r,
                                        temperature=a.temperature, top_k=a.top_k,
                                        calc_enc=enc if a.calculator else None, return_forced=True)
            R = [float(extract_answer(completion_text(enc, o)) == ex["answer"]) for o in outs]
            rewards += R
            if a.algo == "rft":
                seen = set()
                for o, fm, rew in zip(outs, forced, R):
                    if rew > 0 and tuple(o) not in seen:
                        seen.add(tuple(o))
                        seqs.append((prompt, o, 1.0, fm))
                signal += bool(seen)
            else:
                mean = sum(R) / len(R)
                if all(x == R[0] for x in R):  # no learning signal (DAPO dynamic sampling)
                    continue
                signal += 1
                seqs += [(prompt, o, rew - mean, fm) for o, fm, rew in zip(outs, forced, R)]
    return seqs, dict(reward=sum(rewards) / max(1, len(rewards)), groups_with_signal=signal / len(batch))


def policy_loss(model, seqs, a, r, device, amp, norm):
    """Accumulates gradients over micro-batches; returns the summed loss value."""
    total = 0.0
    for i in range(0, len(seqs), a.device_batch):
        mb = seqs[i:i + a.device_batch]
        T = max(len(s[0]) + len(s[1]) for s in mb) - 1
        x = torch.full((len(mb), T), GPT2_EOT, dtype=torch.long)
        y = torch.full((len(mb), T), -1, dtype=torch.long)
        for b, s in enumerate(mb):
            p, c = s[0], s[1]
            full = torch.tensor(p + c)
            x[b, :len(full) - 1] = full[:-1]
            tgt = full[len(p):].clone()
            if len(s) > 3:  # engine-forced calculator output is not the policy's action
                tgt[torch.tensor(s[3], dtype=torch.bool)] = -1
            y[b, len(p) - 1:len(full) - 1] = tgt
        x, y = x.to(device), y.to(device)
        adv = torch.tensor([s[2] for s in mb], device=device)
        with amp:
            out = model(x, num_steps=r, init_state="zero", return_hidden=True, last_only=True,
                        loop_readout=a.loop_credit == "all")
            hs = out["loop_hidden"] if a.loop_credit == "all" else [out["hidden"]]
            loss = 0.0
            for h in hs:
                logp = model.token_logprobs(h, y)  # [B, T]
                loss = loss - (adv[:, None] * logp).sum() / norm
            loss = loss / len(hs)
        loss.backward()
        total += loss.item()
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", required=True)
    ap.add_argument("--algo", choices=["drgrpo", "rft"], default="drgrpo")
    ap.add_argument("--loop-credit", choices=["final", "all"], default="final")
    ap.add_argument("--out-dir", default="runs/rl")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--prompts-per-step", type=int, default=16)
    ap.add_argument("--G", type=int, default=16, help="samples per prompt")
    ap.add_argument("--max-new", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--lr-scale", type=float, default=None,
                    help="x pretraining LRs (default 0.05 drgrpo as in nanochat, 0.2 rft)")
    ap.add_argument("--fixed-steps", type=int, default=None, help="fixed loop count instead of sampling")
    ap.add_argument("--no-calculator", dest="calculator", action="store_false",
                    help="disable engine-run <|calc|> spans in rollouts")
    ap.add_argument("--device-batch", type=int, default=16)
    ap.add_argument("--eval-every", type=int, default=50)
    ap.add_argument("--eval-n", type=int, default=300)
    ap.add_argument("--min-passk", type=float, default=0.3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    random.seed(a.seed)
    torch.manual_seed(a.seed)
    is_cuda = a.device.startswith("cuda")
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if is_cuda else nullcontext()
    enc = gpt2_tokenizer()
    model, ck = load_checkpoint(a.init, a.device)
    model._rng.seed(a.seed)
    train, test = load_source("gsm8k", "train"), load_source("gsm8k", "test")
    os.makedirs(a.out_dir, exist_ok=True)
    logf = open(os.path.join(a.out_dir, "log.jsonl"), "a")

    def log(rec):
        print(" ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in rec.items()), flush=True)
        logf.write(json.dumps(rec) + "\n")
        logf.flush()

    dev_type = "cuda" if is_cuda else "cpu"
    r0 = a.fixed_steps or model.cfg.mean_recurrence
    probe = random.sample(train, min(64, len(train)))
    passk = gsm8k_accuracy(model, enc, probe, r0, dev_type, a.max_new, samples=a.G, temperature=1.0)
    log(dict(step=0, train_pass_at_G=passk, test_pass1=gsm8k_accuracy(model, enc, test[:a.eval_n], r0, dev_type)))
    if passk < a.min_passk and not a.force:
        raise SystemExit(f"pass@{a.G} = {passk:.2f} < {a.min_passk}: too little signal for RL. "
                         "Do task SFT first (sft.py --mix gsm8k-aug:3) or pass --force.")

    lr_scale = a.lr_scale or (0.05 if a.algo == "drgrpo" else 0.2)
    optims = build_optimizers(model, lr_scale=lr_scale)
    steps = int(len(train) * a.epochs / a.prompts_per_step)
    t0 = time.time()
    for step in range(1, steps + 1):
        m = 1 - (step - 1) / steps  # linear decay to 0
        for o in optims:
            for g in o.param_groups:
                g["lr"] = g["initial_lr"] * m
        batch = random.sample(train, a.prompts_per_step)
        r = a.fixed_steps or model.sample_num_steps()
        seqs, stats = rollouts(model, enc, batch, a, r, amp)
        if seqs:
            model.train()
            if a.algo == "drgrpo":
                norm = a.prompts_per_step * a.G * a.max_new  # Dr. GRPO constant normaliser
            else:
                norm = sum(len(s[1]) for s in seqs)
            loss = policy_loss(model, seqs, a, r, a.device, amp, norm)
            for o in optims:
                o.step()
            model.zero_grad(set_to_none=True)
        else:
            loss = 0.0
        log(dict(step=step, loops=r, loss=loss, n_seqs=len(seqs),
                 mean_len=sum(len(s[1]) for s in seqs) / max(1, len(seqs)),
                 elapsed=round(time.time() - t0), **stats))
        if step % a.eval_every == 0 or step == steps:
            log(dict(step=step, test_pass1=gsm8k_accuracy(model, enc, test[:a.eval_n], r0, dev_type)))
            save_checkpoint(os.path.join(a.out_dir, "ckpt_latest.pt"), model, chat_init=True,
                            stage=f"rl:{a.algo}", step=step)
    save_checkpoint(os.path.join(a.out_dir, "ckpt_final.pt"), model, chat_init=True, stage=f"rl:{a.algo}",
                    optims=[o.state_dict() for o in optims])
    print("done")


if __name__ == "__main__":
    main()
