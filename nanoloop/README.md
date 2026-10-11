# NanoLoop

NanoLoop is a GPT-2-sized language model that tests how far a small model can go with 2025–26 techniques. It reuses a small, weight-shared transformer core across a variable number of loops per token. Training samples the loop count. At inference you choose it, or let each token exit early once its prediction stops changing. A second stage teaches the model to reason in continuous "neuralese" thoughts instead of written chain-of-thought.

- **Architecture diagram and technique ledger:** https://claude.ai/artifact/P4s3Y9c1tjk1g47p9y85QL
- **Research behind every choice:** [`docs/RESEARCH.md`](docs/RESEARCH.md)
- **Where to download every dataset:** [`docs/DATASETS.md`](docs/DATASETS.md)

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
python -m pytest tests -q                    # 44 CPU tests: kernels, cache exactness, training, post-training, tools, LOTUS, long context
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
python train.py --preset loop-frontier ...               # + Engram/PLE n-gram memory + 2-stream GatedResidual
                                                         #   (DeepSeek V4.1 / Qwen3.8-Flash-Next pieces, 280M total)
python train.py --preset loop-hybrid ...                 # 3:1 Gated DeltaNet in the loop
python train.py --preset loop-base --set mean_recurrence=8 --set attn_gate=headwise ...
```

**Logs.** Logs go to `runs/<name>/log.jsonl`. Every 2000 steps the trainer logs validation loss at several loop counts (`val_r1 … val_r24`). This tells you whether recurrence is working: loss should keep falling past the training mean.

**Checkpoints.** Resume a run with `--resume runs/<name>/ckpt_latest.pt`.

**Timing (estimate, not yet measured on a 4090):** budget roughly 15–20 h for loop-base at 2.5B tokens. Measure `tok_s` in the first few minutes and size `--tokens` from it.

### Long context (LFM2-style, on a small budget)

LFM2.5-350M reaches 32K with mostly constant-state layers plus 28T tokens. `loop-long` copies the architecture and uses targeted training in place of the token budget.

```bash
# pretrain: constant-state mixers + sequence-length curriculum up to 4K (cheaper than a flat 2K run)
python train.py --preset loop-long --data fineweb-edu --tokens 2.5e9 --seq-len 4096 --device-batch 4 \
    --seq-schedule 512:0.1,1024:0.3,2048:0.6,4096:1.0
# long-context stage: ~200M tokens at 16K with long documents + synthetic retrieval, RoPE base raised
python prepare_data.py pg19 --max-tokens 3e8
python prepare_data.py fineweb-edu --min-doc-tokens 4096 --max-tokens 1e8
python prepare_data.py synth-retrieval --max-tokens 3e7
python train.py --init runs/long/ckpt_final.pt --data pg19:0.4,fineweb-edu-long:0.25,fineweb-edu:0.25,synth-retrieval:0.1 \
    --tokens 2e8 --seq-len 16384 --device-batch 1 --warmup-steps 20 --warmdown-frac 0.5 --lr-scale 0.3 \
    --set rope_base=500000 --set max_seq_len=32768
# measure usable context (and try training-free extension on any checkpoint)
python eval_niah.py runs/long2/ckpt_final.pt --lengths 2048,4096,8192,16384,32768
python eval_niah.py runs/base/ckpt_final.pt --rope-scaling yarn --rope-factor 4
```

**Context limits:**
- `loop-base` trains at 2K, with a 4K RoPE table as the hard limit. Checkpoints record their trained length (`context_len`), and the agent budgets prompts against it.
- `loop-long` after the long-context stage: 16–32K. Expect dependable retrieval up to about 8K (estimate).

## 3. Evaluate and sample

```bash
python eval_hellaswag.py runs/<name>/ckpt_final.pt --steps 1,2,4,6,12,24   # accuracy vs thinking depth
python sample.py runs/<name>/ckpt_final.pt --prompt "The Moon is" --steps 12
python sample.py runs/<name>/ckpt_final.pt --prompt "..." --steps 32 --exit-threshold 1e-3  # adaptive depth
```

Targets to beat (GPT-2 124M):
- FineWeb val loss 3.28. Train with `--data fineweb-edu --val-data fineweb10B` to report it.
- HellaSwag 29.4.

## 4. Post-training

The stages run in order. Each one is an independent script. The research behind it is in `docs/RESEARCH.md` §5.

```bash
# A — decay-phase mid-training: switch the data mix during the LR warmdown, then average the last weights
python prepare_data.py finemath --max-tokens 1e9 && python prepare_data.py cosmopedia-v2 --max-tokens 5e8
python prepare_data.py chat-mix
python train.py --preset loop-base --data fineweb-edu --tokens 2.5e9 \
    --decay-data fineweb-edu:0.55,finemath:0.2,cosmopedia-v2:0.1,chat-mix:0.15      # -> ckpt_final_avg.pt
#   (already pretrained? run only the decay phase:)
#   python train.py --init runs/base/ckpt_final.pt --data <mix> --tokens 5e8 --warmup-steps 0 --warmdown-frac 1

# B — general chat SFT (+ calculator and tool calling), then WiSE-merge with the base
python sft.py --init runs/base/ckpt_final_avg.pt --out-dir runs/sft \
    --mix smoltalk:1,mmlu:1,gsm8k-calc:4,tools-synth:1,xlam:0.5,hermes:1
python merge.py runs/sft/ckpt_final.pt runs/base/ckpt_final_avg.pt --weights 0.875,0.125 --out runs/sft/wise.pt

# C — task SFT: GSM8k-Aug explicit chain-of-thought with inline calculator calls
python sft.py --init runs/sft/wise.pt --mix gsm8k-aug-calc:3 --out-dir runs/sft-math

# D — online rejection-sampling finetuning (keep only correct samples)
python rl.py --init runs/sft-math/ckpt_final.pt --algo rft --out-dir runs/rft

# E — Dr. GRPO RL (add --loop-credit all for RLTT per-loop credit)
python rl.py --init runs/rft/ckpt_final.pt --algo drgrpo --out-dir runs/grpo

# after every stage: accuracy vs thinking depth
python eval_gsm8k.py runs/grpo/ckpt_final.pt --steps 1,2,4,6,12,24
python sample.py runs/sft/wise.pt --chat "Explain photosynthesis to a 10 year old."
```

Guardrails built into the scripts:
- `rl.py` measures pass@16 first and refuses to start below 30%, because RL makes tiny untuned models worse.
- Every stage keeps the pretraining loop-count distribution.
- RL rollouts and updates use the same loop count, so training stays on-policy.

Timing (estimates, not measured): about 15–35 GPU-hours on a 4090 for stages A–E.

## 5. Tools and agents

```bash
python agent.py runs/sft/wise.pt                          # chat; the model may call calculator / convert_units / word_count
python agent.py runs/sft/wise.pt --once "Convert 12 km to mi"
```

- Tool calls use dedicated special tokens with a JSON body.
- Decoding is constrained: names are limited to registered tools and arguments to valid JSON, so every call parses.
- Tool results are fed back for up to 3 agent steps.
- Math uses an inline calculator that the engine executes.

To add a tool:
1. Define a `Tool` in `nanoloop/tools.py`.
2. Generate ~500–1000 examples of it (template: `tools-synth` in `nanoloop/tool_data.py`).
3. Finetune with `sft.py`.

Realistic expectations at this size: reliable single calls on familiar phrasing, and no open-ended multi-step agency. See `docs/RESEARCH.md` §7.

## 6. Stage F: latent reasoning

**Frontier: LOTUS parallel latent workspace** (2026). The looped core refines all latent slots at once, and every slot is supervised.

```bash
python lotus.py --init runs/sft-math/ckpt_final.pt --out-dir runs/lotus
python lotus.py --eval-only runs/lotus/ckpt_final.pt --eval-steps 2,4,6,8,12 --show 3   # + shortcut test
```

**Baseline: Coconut + CODI.**

```bash
python coconut.py --init runs/sft-math/ckpt_final.pt --cot-epochs 0 --out-dir runs/coconut  # from stage C
# or straight from a pretrained base: python coconut.py --init runs/<name>/ckpt_final.pt
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
nanoloop/chat.py       chat template, answer parsing, SFT data sources
nanoloop/engine.py     batched KV-cached group sampling, GSM8K accuracy
train.py  prepare_data.py  sample.py  eval_hellaswag.py  eval_gsm8k.py
nanoloop/tools.py      calculator, tool registry, JSON-prefix validator
nanoloop/agent.py      constrained tool-call decoding + agent loop
nanoloop/tool_data.py  xlam / hermes / smoltalk2 / synthetic tool data
nanoloop/ngram.py      Engram/PLE hashed n-gram memory
nanoloop/longctx.py    synthetic needle / key-value retrieval data (training + NIAH eval)
sft.py  rl.py  merge.py  agent.py  lotus.py  coconut.py  eval_niah.py
```
