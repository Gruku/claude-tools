# NanoLoop

NanoLoop is a GPT-2-sized language model that tests how far a small model can go with 2025–26 techniques. It reuses a small, weight-shared transformer core across a variable number of loops per token. Training samples the loop count. At inference you choose it, or let each token exit early once its prediction stops changing. A second stage teaches the model to reason in continuous "neuralese" thoughts instead of written chain-of-thought.

- **Architecture diagram and technique ledger:** https://claude.ai/artifact/P4s3Y9c1tjk1g47p9y85QL
- **Research behind every choice:** [`docs/RESEARCH.md`](docs/RESEARCH.md)

```
tokens → embed+smear → PRELUDE×2 → e=norm(·) ─┐
                    s₀~N(0,σ²) → [ adapter([s;e]) → CORE×4 ]×r → CODA×2 (+U-net skips) → softcapped head
                                   r ~ LogNormalPoisson(6), backprop last 4 loops
```

| | loop-base (default) | dense-base (control) |
|---|---|---|
| total params | 217M | 248M |
| transformer-block params | 61M | 92M |
| effective depth | 28 layers at r=6 (any r at inference) | 12 |
| train FLOPs/token (T=2048) | 1.74 G | 1.02 G |

What goes into each layer:
- Gated attention with QK-norm, partial RoPE, gated XSA, value embeddings and value residual.
- A ReLU² MLP.
- Zero-initialized output projections.

Optimization uses Muon (Polar Express + NorMuon + cautious WD) for hidden matrices and AdamW for embeddings, head and scalars. The LR schedule is WSD. See the ledger for the source paper behind each piece.

## Setup

Requirements: Python 3.10+, PyTorch ≥ 2.5, and a CUDA GPU (24 GB is comfortable).

**Use Linux or WSL2 on Windows**, and keep the data on the Linux filesystem rather than `/mnt/c`. Native Windows works only with `triton-windows` installed, because `torch.compile` needs it. Without it, pass `--no-compile` (expect it to be slower).

```bash
pip install -r requirements.txt
# optional speedups:
pip install flash-attn --no-build-isolation   # native sliding windows (loop-swa preset)
pip install flash-linear-attention           # Triton Gated DeltaNet kernels (loop-hybrid preset)
python -m pytest tests -q                    # 14 CPU tests: kernels, causality, cache exactness, training
```

## 1. Data

```bash
python prepare_data.py fineweb-edu --max-tokens 5e9      # quality pretraining corpus (local tokenization)
python prepare_data.py fineweb10B --train-shards 1       # just to get the FineWeb val shard for the 3.28 benchmark
# alternative corpus that nanochat measured as best: python prepare_data.py climbmix --max-tokens 5e9
```

## 2. Pretrain

```bash
# smoke test: runs anywhere in about a minute
python train.py --preset tiny --data synthetic --device cpu --seq-len 64 --batch-tokens 1024 --max-steps 100

# the main run: 2.5B tokens on FineWeb-Edu
python train.py --preset loop-base --data fineweb-edu --tokens 2.5e9
# out of memory: --device-batch 4 (accumulation adjusts automatically) or --checkpoint-core

# the control run (same tokens), plus optional ablations
python train.py --preset dense-base --data fineweb-edu --tokens 2.5e9
python train.py --preset loop-hybrid ...                 # 3:1 Gated DeltaNet in the loop
python train.py --preset loop-base --set mean_recurrence=8 --set attn_gate=headwise ...
```

**Logs.** Logs go to `runs/<name>/log.jsonl`. Every 2000 steps the trainer logs validation loss at several loop counts (`val_r1 … val_r24`). This tells you whether recurrence is working: loss should keep falling past the training mean.

**Checkpoints.** Resume a run with `--resume runs/<name>/ckpt_latest.pt`.

**Timing (estimate, not yet measured on a 4090):** budget roughly 15–20 h for loop-base at 2.5B tokens. Measure `tok_s` in the first few minutes and size `--tokens` from it.

## 3. Evaluate and sample

```bash
python eval_hellaswag.py runs/<name>/ckpt_final.pt --steps 1,2,4,6,12,24   # accuracy vs thinking depth
python sample.py runs/<name>/ckpt_final.pt --prompt "The Moon is" --steps 12
python sample.py runs/<name>/ckpt_final.pt --prompt "..." --steps 32 --exit-threshold 1e-3  # adaptive depth
```

Targets to beat (GPT-2 124M):
- FineWeb val loss 3.28. Train with `--data fineweb-edu --val-data fineweb10B` to report it.
- HellaSwag 29.4.

## 4. Stage 2: latent reasoning (Coconut + CODI on GSM8k-Aug)

```bash
python coconut.py --init runs/<name>/ckpt_final.pt --out-dir runs/coconut
python coconut.py --eval-only runs/coconut/stage3.pt --eval-steps 2,4,8,16
```

The stages run in order:
1. CoT SFT.
2. A curriculum that replaces 1, 2, then 3 reasoning steps with 2 continuous thoughts each.
3. All language reasoning is dropped, leaving 6 thoughts before the answer.

A thought is the model's own last hidden state, fed back as the next input. GPT-2-scale references on GSM8K:

| Method | GSM8K |
|---|---|
| No-CoT | 16.5% |
| Coconut | 34.1% |
| Explicit CoT | 42.9% |
| CODI | 43.7% |

## Layout

```
nanoloop/config.py     presets + every architectural default
nanoloop/layers.py     RMSNorm, partial RoPE, gated attention, ReLU² MLP, KV cache
nanoloop/deltanet.py   Gated DeltaNet (fla kernels or exact PyTorch fallback)
nanoloop/model.py      the looped model, adaptive exit, cache sharing, generate()
nanoloop/optim.py      Muon (Polar Express + NorMuon + cautious WD) + AdamW groups
nanoloop/data.py       llm.c-format token shards
train.py  prepare_data.py  sample.py  eval_hellaswag.py  coconut.py
```
