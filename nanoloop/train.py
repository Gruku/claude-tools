"""Pretrain NanoLoop on a single GPU (or several via torchrun).

  python train.py --preset loop-base --data fineweb-edu --tokens 2.5e9
  python train.py --preset dense-base --data fineweb-edu --tokens 2.5e9   # control
  python train.py --preset tiny --data synthetic --max-steps 50 --device cpu  # smoke test

Override any ModelConfig field: --set mean_recurrence=8 --set attn_gate=headwise
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from contextlib import nullcontext

import torch
import torch.distributed as dist

from nanoloop.config import ModelConfig, make_config
from nanoloop.data import TokenLoader, make_loader, parse_data_spec
from nanoloop.model import NanoLoop
from nanoloop.optim import build_optimizers


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", default="loop-base")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a ModelConfig field")
    ap.add_argument("--data", default="fineweb-edu",
                    help="name under --data-dir, a weighted mix 'a:0.7,b:0.3', or 'synthetic'")
    ap.add_argument("--decay-data", default=None,
                    help="mix used during the LR warmdown (stage A mid-training), e.g. "
                         "'fineweb-edu:0.55,finemath:0.2,cosmopedia-v2:0.1,chat-mix:0.15'")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--val-data", default=None, help="val set name (default: same as --data)")
    ap.add_argument("--out-dir", default=None)
    # budget & batch
    ap.add_argument("--tokens", type=float, default=2.5e9, help="total training tokens")
    ap.add_argument("--batch-tokens", type=int, default=2 ** 19)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--device-batch", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None, help="cap steps (smoke tests)")
    ap.add_argument("--seq-schedule", default=None,
                    help="sequence-length curriculum 'len:until_frac,...' ending at --seq-len, e.g. "
                         "'512:0.1,1024:0.3,2048:0.6,4096:1.0'. Tokens per step stay constant (the "
                         "micro-batch grows as sequences shrink), so short early steps are cheaper")
    # optimisation
    ap.add_argument("--lr-scale", type=float, default=1.0)
    ap.add_argument("--warmup-steps", type=int, default=100)
    ap.add_argument("--warmdown-frac", type=float, default=0.5)
    ap.add_argument("--final-lr-frac", type=float, default=0.05)
    ap.add_argument("--recurrence-ramp-frac", type=float, default=None,
                    help="ramp mean loop count from 2 to target over this fraction of training "
                         "(default 0.15 from scratch, 0 with --init/--resume: keep the pretraining "
                         "loop distribution)")
    ap.add_argument("--mtp", default="", help="same-head MTP weights, e.g. '0.5,0.25' (annealed to 0)")
    ap.add_argument("--grad-clip", type=float, default=0.0)
    ap.add_argument("--checkpoint-core", action="store_true", help="activation-checkpoint loops")
    # eval / io
    ap.add_argument("--eval-every", type=int, default=250)
    ap.add_argument("--eval-tokens", type=int, default=4 * 2 ** 20)
    ap.add_argument("--profile-every", type=int, default=2000,
                    help="val loss vs loop count every N steps (0 = only at the end)")
    ap.add_argument("--save-every", type=int, default=1000)
    ap.add_argument("--resume", default=None, help="continue a run exactly (step, data, optimizer)")
    ap.add_argument("--init", default=None,
                    help="start from a checkpoint's weights+optimizer with a fresh schedule "
                         "(e.g. a decay-only mid-training run: --warmup-steps 0 --warmdown-frac 1)")
    ap.add_argument("--avg-frac", type=float, default=0.1,
                    help="average weights over the final fraction of steps -> ckpt_final_avg.pt")
    ap.add_argument("--avg-every", type=int, default=25)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--no-compile", action="store_true")
    ap.add_argument("--peak-tflops", type=float, default=165.0, help="for MFU (4090 bf16=165)")
    return ap.parse_args()


def coerce(v: str):
    for fn in (int, float):
        try:
            return fn(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v.lower(), v)


class SyntheticLoader:
    """Random-walk tokens with learnable structure, for CPU smoke tests."""

    def __init__(self, B, T, vocab, seed=0):
        self.B, self.T, self.V = B, T, vocab
        self.g = torch.Generator().manual_seed(seed)

    def next_batch(self, device="cpu", B=None, T=None):
        B, T = B or self.B, T or self.T
        start = torch.randint(0, self.V, (B, 1), generator=self.g)
        steps = torch.randint(1, 4, (B, T), generator=self.g)
        seq = torch.cat([start, (start + steps.cumsum(1)) % self.V], dim=1)
        return seq[:, :-1].to(device), seq[:, 1:].to(device)

    def state_dict(self):
        return {}

    def load_state_dict(self, st):
        pass


def lr_mult(step, total, warmup, warmdown_frac, final):
    if step < warmup:
        return (step + 1) / warmup
    wd_start = int(total * (1 - warmdown_frac))
    if step < wd_start:
        return 1.0
    frac = (step - wd_start) / max(1, total - wd_start)
    return 1.0 - frac * (1.0 - final)


@torch.no_grad()
def evaluate(model, loader_factory, n_tokens, B, T, device, amp, num_steps=None):
    model.eval()
    loader = loader_factory()
    n_batches = max(1, n_tokens // (B * T))
    total = 0.0
    for _ in range(n_batches):
        x, y = loader.next_batch(device)
        with amp:
            total += model(x, y, num_steps=num_steps)["loss"].item()
    model.train()
    return total / n_batches


def main():
    a = parse_args()
    ddp = int(os.environ.get("WORLD_SIZE", 1)) > 1
    if ddp:
        dist.init_process_group("nccl")
        rank, world = dist.get_rank(), dist.get_world_size()
        device = f"cuda:{int(os.environ['LOCAL_RANK'])}"
        torch.cuda.set_device(device)
    else:
        rank, world = 0, 1
        device = a.device if a.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    master = rank == 0
    torch.manual_seed(a.seed + rank)
    is_cuda = device.startswith("cuda")
    if is_cuda:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if is_cuda else nullcontext()

    src = a.resume or a.init
    ck = torch.load(src, map_location=device, weights_only=False) if src else None
    if ck is not None:  # the checkpoint's config wins over --preset; with --init, --set
        # may still change non-parameter fields (rope_base, max_seq_len, rope_scaling, ...)
        over = {k: coerce(v) for k, v in (s.split("=", 1) for s in a.set)} if a.init else {}
        cfg = ModelConfig(**{**ck["config"], **over})
    else:
        cfg = make_config(a.preset, **{k: coerce(v) for k, v in (s.split("=", 1) for s in a.set)})
    model = NanoLoop(cfg, seed=a.seed).to(device)
    model.checkpoint_core = a.checkpoint_core
    out_dir = a.out_dir or os.path.join("runs", f"{a.preset}-{time.strftime('%Y%m%d-%H%M%S')}")

    B, T = a.device_batch, a.seq_len
    assert a.batch_tokens % (B * T * world) == 0, "batch-tokens must divide by device_batch*seq_len*world"
    accum = a.batch_tokens // (B * T * world)
    total_steps = int(a.tokens // a.batch_tokens)
    if a.max_steps:
        total_steps = min(total_steps, a.max_steps)

    if a.data == "synthetic":
        train_loader = SyntheticLoader(B, T, cfg.vocab_size, seed=a.seed + rank)
        val_factory = lambda: SyntheticLoader(B, T, cfg.vocab_size, seed=10_000)
    else:
        train_loader = make_loader(a.data, a.data_dir, B, T, rank, world, a.seed)
        vname = a.val_data or parse_data_spec(a.data)[0][0]
        vroot = os.path.join(a.data_dir, vname)
        val_factory = lambda: TokenLoader(os.path.join(vroot, "*_val_*.bin"), B, T, rank, world)

    decay_loader = (make_loader(a.decay_data, a.data_dir, B, T, rank, world, a.seed + 1)
                    if a.decay_data else None)
    optims = build_optimizers(model, lr_scale=a.lr_scale)
    lrs = [[g["initial_lr"] for g in o.param_groups] for o in optims]
    step = 0
    if ck is not None:
        model.load_state_dict({k.replace("._orig_mod", ""): v for k, v in ck["model"].items()})
        if ck.get("optims"):
            for o, s, group_lrs in zip(optims, ck["optims"], lrs):
                o.load_state_dict(s)
                for g, lr in zip(o.param_groups, group_lrs):
                    g["initial_lr"] = lr  # --lr-scale of this run wins
        if a.resume:
            train_loader.load_state_dict(ck["loader"])
            if decay_loader is not None and ck.get("decay_loader"):
                decay_loader.load_state_dict(ck["decay_loader"])
            model._rng.setstate(ck["rng"])
            step = ck["step"]
            out_dir = os.path.dirname(a.resume)

    if not a.no_compile and is_cuda:
        for blk in [*model.prelude, *model.core, *model.coda]:
            blk.compile(dynamic=False)

    schedule = []
    if a.seq_schedule:
        for part in a.seq_schedule.split(","):
            L, _, frac = part.partition(":")
            schedule.append((int(L), float(frac)))
        assert schedule[-1][0] == T and schedule[-1][1] >= 1.0, "schedule must end at --seq-len:1.0"
        assert all(T % L == 0 for L, _ in schedule), "every length must divide --seq-len"
        assert T <= cfg.max_seq_len, "--seq-len exceeds max_seq_len"

    def seq_len_at(step):
        frac = step / max(1, total_steps)
        return next((L for L, until in schedule if frac < until), T) if schedule else T

    cfg.context_len = max(cfg.context_len, T)  # recorded in every checkpoint
    mtp_w = [float(w) for w in a.mtp.split(",") if w]
    flops_tok = model.flops_per_token(T)
    if master:
        os.makedirs(out_dir, exist_ok=True)
        pc = model.param_counts()
        print(f"config: {json.dumps(cfg.to_dict())}")
        print("params: " + ", ".join(f"{k}={v / 1e6:.1f}M" for k, v in pc.items()))
        print(f"effective depth at r={cfg.mean_recurrence}: {cfg.effective_depth()} layers; "
              f"~{flops_tok / 1e9:.2f} GFLOP/token train")
        print(f"steps={total_steps} accum={accum} batch_tokens={a.batch_tokens} out={out_dir}")
        with open(os.path.join(out_dir, "config.json"), "w") as f:
            json.dump(dict(model=cfg.to_dict(), args=vars(a)), f, indent=2)
    logf = open(os.path.join(out_dir, "log.jsonl"), "a") if master else None

    def log(rec):
        if master:
            print(" ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in rec.items()),
                  flush=True)
            logf.write(json.dumps(rec) + "\n")
            logf.flush()

    def save(tag):
        if not master:
            return
        path = os.path.join(out_dir, f"ckpt_{tag}.pt")
        torch.save(dict(model=model.state_dict(), optims=[o.state_dict() for o in optims],
                        loader=train_loader.state_dict(), rng=model._rng.getstate(), step=step,
                        decay_loader=decay_loader.state_dict() if decay_loader else None,
                        config=cfg.to_dict()), path)
        print(f"saved {path}")

    # Uniform average of the weights over the end of the warmdown: approximates
    # (and stacks with) annealing, per "Model Merging in Pre-training" 2505.12082.
    avg_start = int(total_steps * (1 - a.avg_frac)) if a.avg_frac > 0 else None
    avg_state, avg_n = None, 0

    def accumulate_average():
        nonlocal avg_state, avg_n
        avg_n += 1
        with torch.no_grad():
            if avg_state is None:
                avg_state = {k: v.detach().float().cpu().clone() for k, v in model.state_dict().items()}
            else:
                for k, v in model.state_dict().items():
                    avg_state[k] += (v.detach().float().cpu() - avg_state[k]) / avg_n

    def profile():
        rs = sorted({1, 2, 4, cfg.mean_recurrence, 2 * cfg.mean_recurrence,
                     4 * cfg.mean_recurrence})
        rec = {"step": step}
        for r in rs:
            rec[f"val_r{r}"] = evaluate(model, val_factory, a.eval_tokens // 4, B, T, device, amp, r)
        log(rec)

    model.train()
    t_last, tok_last = time.time(), 0
    ramp_frac = a.recurrence_ramp_frac
    if ramp_frac is None:
        ramp_frac = 0.0 if (a.init or a.resume) else 0.15
    ramp_steps = int(total_steps * ramp_frac)
    while step < total_steps:
        m = lr_mult(step, total_steps, a.warmup_steps, a.warmdown_frac, a.final_lr_frac)
        for o in optims:
            for g in o.param_groups:
                g["lr"] = g["initial_lr"] * m
        optims[1].param_groups[0]["momentum"] = 0.85 + 0.10 * min(1.0, step / 300)
        mean_r = cfg.mean_recurrence
        if ramp_steps and step < ramp_steps and cfg.sample_recurrence:
            mean_r = 2 + (cfg.mean_recurrence - 2) * step / ramp_steps
        mtp = [w * (1 - step / total_steps) for w in mtp_w]

        loss_acc, steps_acc = 0.0, 0
        in_decay = step >= int(total_steps * (1 - a.warmdown_frac))
        loader = decay_loader if (decay_loader is not None and in_decay) else train_loader
        T_now = seq_len_at(step)
        for _ in range(accum):
            x, y = loader.next_batch(device, B * T // T_now, T_now)
            r = model.sample_num_steps(mean_r)
            with amp:
                out = model(x, y, num_steps=r, mtp_weights=mtp)
            (out["loss"] / accum).backward()
            loss_acc += out["loss"].item() / accum
            steps_acc += r
        if ddp:
            for p in model.parameters():
                if p.grad is not None:
                    dist.all_reduce(p.grad, op=dist.ReduceOp.AVG)
        if a.grad_clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), a.grad_clip)
        for o in optims:
            o.step()
        model.zero_grad(set_to_none=True)
        step += 1
        tok_last += a.batch_tokens

        if not math.isfinite(loss_acc):
            raise RuntimeError(f"non-finite loss at step {step}")
        if step % 10 == 0 or step == total_steps:
            if is_cuda:
                torch.cuda.synchronize()
            dt = time.time() - t_last
            tps = tok_last / dt
            log(dict(step=step, loss=loss_acc, lr_mult=m, mean_r=round(steps_acc / accum, 2), seq_len=T_now,
                     tok_s=round(tps), mfu=tps * flops_tok / (a.peak_tflops * 1e12 * world),
                     tokens=step * a.batch_tokens))
            t_last, tok_last = time.time(), 0
        if step % a.eval_every == 0 or step == total_steps:
            log(dict(step=step, val_loss=evaluate(model, val_factory, a.eval_tokens, B, T, device, amp)))
        if (a.profile_every and step % a.profile_every == 0) or step == total_steps:
            profile()
        if avg_start is not None and step > avg_start and (step % a.avg_every == 0 or step == total_steps):
            accumulate_average()
        if step % a.save_every == 0 or step == total_steps:
            save("latest" if step < total_steps else "final")
        if step == total_steps and avg_state is not None and master:
            path = os.path.join(out_dir, "ckpt_final_avg.pt")
            torch.save(dict(model=avg_state, config=cfg.to_dict(), averaged=avg_n,
                            optims=[o.state_dict() for o in optims]), path)
            print(f"saved {path} (average of {avg_n} snapshots)")

    if ddp:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
