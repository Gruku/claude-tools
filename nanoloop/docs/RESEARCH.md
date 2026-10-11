# NanoLoop research notes (October 2026)

These notes condense the research sweeps behind NanoLoop's design. Each sweep searched papers, repositories and records from 2024 to October 2026. Tags:
- **[code]**: read directly from the official repository.
- **[abs]**: abstract or secondary summary only.
- **[mem]**: not re-verified. Check before citing.

The sweeps were:
1. Attention, KV cache and sequence mixing.
2. Recurrent depth and latent ("neuralese") reasoning.
3. Small-model training recipes.
4. Post-training. Added at the end of this file.

---

## 1. Recurrent depth: the main bet

**Huginn: "Scaling up Test-Time Compute with Latent Reasoning" (arXiv 2502.05171) [code]**
- Layout: a prelude P, then a core R iterated r times, then a coda C. Every iteration runs `s = core(adapter([s; e]))`, where e is the prelude output.
- The released 3.5B model uses 2/4/2 layers. It was trained on 800B tokens with r̄=32.
- Sampling:
  - The loop count is drawn from a log-normal Poisson with σ=0.5.
  - Only the last k=8 loops are backpropagated.
  - The initial state is s₀ ~ TruncNormal(std √(2/5)).
- Blocks use a sandwich norm: `n2(x + attn(n1 x))`.
- Adaptive exit is training-free: stop when KL(p_t‖p_{t−1}) < 1e-3.
- KV caches can be shared across iterations. A token reads the latest computed state of earlier tokens, using slots taken modulo 4.
- Failure modes from the paper [mem]:
  - States collapse to token-independent values.
  - The model learns to ignore the recurrence.
  - Fixes were sandwich norm, careful init and embedding scale, and a modest LR.

**Ouro / LoopLM (arXiv 2510.25741) [abs]**
- Loops the whole stack 4 times.
- Adds an LM loss at every step plus a learned exit gate with an entropy regularizer.
- Ouro-1.4B-R4 roughly matches 4B dense models.
- Loss spikes appeared at 8 steps and were resolved by going back to 4.
- Follow-up "Closing the Loop" (arXiv 2610.00673): a 1.4B LoopLM beats its parameter-matched dense twin on 12/12 benchmarks [abs].

**Parcae (arXiv 2604.12946) [abs]**
- Treats the loop as a dynamical system.
- Constrains the spectral radius of the injection and normalizes the injected embedding to avoid late-stage loss spikes.
- FLOP-optimal training scales loop count together with data.

**Mixture-of-Recursions (arXiv 2507.10524) [abs]**
- Routes a recursion depth to each token. Pareto gains from 135M to 1.7B.
- Requires routers and depth-aware KV caching.

**Retrofitted recurrence (arXiv 2511.07384) [abs]**
- Converts a pretrained dense model into a looped one.
- A curriculum that ramps the mean recurrence helps.

**TRM (arXiv 2510.04871) and HRM (arXiv 2506.21734)**
- Tiny recursive networks for ARC and Sudoku.
- Lessons that transfer: deep supervision and EMA weights. Neither model is a language model.

**What NanoLoop takes**
- Huginn's layout, sampling, truncated BPTT, sandwich norm and cache sharing, at r̄=6, k=4, cap 16.
- Parcae's normalized injection.
- A loop-count ramp from retrofitted recurrence.
- KL-based adaptive exit at inference.

**Deferred:** Ouro's exit gates and MoR routers. Revisit both if the basic loop works.

**Compute.** At r̄=6 and k=4, a training token costs about 1.74 GFLOP. The 12-layer dense control costs about 1.02 GFLOP. Compare runs at equal tokens and at equal FLOPs.

## 2. Attention and the KV cache

| Technique | Evidence | Decision |
|---|---|---|
| Gated attention: `Y·σ(XW_g)` after SDPA (arXiv 2505.06708) | PPL 6.03 → 5.76 in ablations. Removes sinks and massive activations. Used in Qwen3-Next | **default**, elementwise |
| QK-norm (OLMo 2, Qwen3, Gemma 3 arXiv 2503.19786) | Replaces attention softcap; makes QK-clip unnecessary | **default**, scale 0.12 |
| Partial RoPE (arXiv 2410.06205; modded-nanogpt) | Rotates half the dims; the other half are content channels. nanochat saw no gain | **default** 50%, ablate |
| Exclusive self-attention, gated (arXiv 2603.09078) | Beats SDPA up to 2.7B; modded-nanogpt record #82 | **default**, α init 0 |
| Value residual (arXiv 2410.17897) + value embeddings | Same loss with 16% fewer params; speedrun staple | **default** |
| Learned sink logits (gpt-oss) | Overlaps with the output gate | skipped |
| Sliding window 3:1–5:1 (Gemma 3, gpt-oss, nanochat SSSL) | Saves little at ≤2k context | preset `loop-swa` |
| Gated DeltaNet hybrid 3:1 (arXiv 2412.06464; Qwen3-Next; Kimi Linear arXiv 2510.26692) | Parity or slight win at 340M–1.3B; recall needs some full attention. 3:1–6:1 is the sweet spot (arXiv 2507.06457) | preset `loop-hybrid` |
| MLA, TPA, MFA, NSA, MoBA, DSA | Benefits appear only at long context and scale | skipped |
| Differential attention, FoX, PaTH, Canon layers | Need custom kernels or overlap with the above | future ablations |

**fla API notes [code]**
- Signature: `chunk_gated_delta_rule(q, k, v, g, beta, scale, initial_state, output_final_state, use_qk_l2norm_in_kernel, ...)`.
- Layout is `[B, T, H, D]`. g is a log decay ≤ 0, and beta is post-sigmoid.
- `head_first` has been removed, so pin your fla version.
- NanoLoop ships an exact pure-PyTorch fallback (WY chunked form). It matches the recurrent form to 1e-7.

## 3. Training recipe

**modded-nanogpt speedrun**
- The current record (#92, Aug 2026) reaches the 3.28 FineWeb val loss in about 40 s on 8×H100.
- Its latest tricks are not portable to one 24 GB GPU:
  - an 84.6M-row hashed n-gram table;
  - FP8 MLPs;
  - FA3, which is Hopper-only.
- Portable pieces, by record:
  - #3: Muon.
  - #5: ReLU², QK-norm, zero-init projections.
  - #8: untied head.
  - #9: logit softcap.
  - #11: U-net skips.
  - #14–16: value embeddings.
  - #34: smear.
  - #38: Polar Express.
  - #41: NorMuon.
  - #43: cautious WD.
  - #82: XSA.

**nanochat (current, Jul 2026)**
- Architecture: 32k BPE, ReLU², QK-norm, parameter-free RMSNorm, untied head, softcap 15, SSSL windows, gated value embeddings, smear.
- Optimizers:
  - Muon side: Polar Express, NorMuon and cautious WD, lr 0.02.
  - AdamW side: embeddings 0.3, head 0.008.
- Schedule: warmdown over the last 65% to 0.05×.
- Negative results: MTP, SwiGLU, MoE, grad clipping, EMA, partial RoPE.
- ClimbMix-400B was the only dataset that beat FineWeb-Edu (27% faster to GPT-2 CORE).

**Optimizer.** Muon is about 1.4× better than well-tuned AdamW at 0.1B, shrinking to 1.1× at 1.2B (arXiv 2509.02046).

**Polar Express coefficients (arXiv 2505.16932)**, 5 iterations:
`(8.1566,−22.4833,15.8788), (4.0429,−2.8089,0.5), (3.8917,−2.7725,0.5061), (3.2858,−2.3681,0.4645), (2.3465,−1.7098,0.4232)`.

**Schedule.** WSD: short warmup, a flat phase, then linear decay to a few percent or zero (arXiv 2405.18392, 2502.15938).

**Batch.** 2¹⁹ tokens for runs up to about 2.5B tokens, and 2²⁰ around 10B tokens (nanochat B ∝ D^0.383).

**Single GPU**
- An RTX 4090 gives 165 TFLOPS bf16. A community single-4090 speedrun port reports 130–163k tok/s for a dense 124M model with FP8.
- Expect about 2× fewer tok/s for loop-base at r̄=6.
- Prefer WSL2 or Linux. Native Windows needs triton-windows to use `torch.compile`.

**Reference numbers**

| Model | HellaSwag | Other |
|---|---|---|
| GPT-2 124M | 29.4 | CORE 0.114; the 3.28 FineWeb val target |
| SmolLM2-135M | 42.1 | 2T tokens |

## 4. Latent reasoning (stage 2)

**Coconut (arXiv 2412.06769) [code]**
- Special tokens: `<|start-latent|> <|latent|>×n <|end-latent|>`. Each latent slot receives the previous position's last hidden state.
- Curriculum: c=2 thoughts per removed step, 3 epochs per stage, 3 stages, then all language reasoning is dropped. The optimizer is reset at each stage.
- Data: GSM8k-Aug (`whynlp/gsm8k-aug`, about 385k rows).
- GPT-2 GSM8K results: no-CoT 16.5, Coconut 34.1, CoT 42.9.

**CODI (arXiv 2502.21074) [code]**
- The same model is both teacher (with CoT) and student (with latents).
- Loss: L1 on the hidden state at the answer anchor, divided by the teacher's std.
- Reaches 43.7% on GPT-2, about the level of explicit CoT.

**Follow-ups**
- SIM-CoT (arXiv 2509.20317): step-level supervision of the latents. +8.2 over Coconut.
- PMPS (arXiv 2609.09928): claims to beat CoT-SFT on GPT-2 [abs].
- LOTUS (arXiv 2606.31779): loops plus supervised latents close the gap to explicit CoT at 3B [abs].

**Caution.** arXiv 2512.21711 finds Coconut latents behave like placeholders. Run perturbation tests before claiming the latents reason.

**What NanoLoop takes.** The Coconut curriculum, the CODI distillation term, and a zero-initialized latent projector. With the looped core there are two compute dials: loops per token and number of thoughts.

---

## 5. Post-training

**Calibration.** General chat at about 200M parameters stays weak whatever you do. Numbers become real only on narrow, task-finetuned targets.

| Model | Benchmark | Result |
|---|---|---|
| SmolLM2-135M-Instruct | IFEval | 29.9 |
| | GSM8K (5-shot) | 1.4 |
| nanochat d20 (561M) | GSM8K | 4.6 after SFT, 7.6 after RL |
| GPT-2 124M on GSM8k-Aug | GSM8K | 42.9 (CoT), 34.1 (Coconut), about 43 (CODI) |

| Technique | Evidence | Relevance at about 200M |
|---|---|---|
| Decay-phase mid-training: math, code and QA in the last 10–20% of tokens | SmolLM2 decay mix is about 58% web, 24% code, 14% math, 4% Cosmopedia (2502.02737). OLMo 3 Dolmino. SmolLM3 reasoning mid-training | **High, almost free.** Biggest lever for ARC and GSM8K readiness |
| SFT: smol-smoltalk + MMLU-aux + GSM8K (nanochat `chat_sft.py`) | Assistant-only loss. Packing with padding, never cropping. Warm-started optimizer with init LR 0.8× | High. Gives coherent chat and an IFEval of about 20–30 |
| DPO family (APO-zero, SimPO, length-normalized DPO, Delta Learning 2507.06187) | SmolLM2-135M used DPO with LR 1e-6, β 0.5 | Low. A few IFEval points; no help on reasoning |
| RLVR: GRPO, Dr. GRPO (2503.20783), DAPO (2503.14476), nanochat REINFORCE | Fails below about 0.5B on raw base models (TinyZero; L20-Edu-135M got worse). Works after task SFT (Nautile-370M: 28 → 33) | Use **only** when pass@16 on train prompts is above 30% |
| Rejection-sampling FT / expert iteration (STaR) | Positive-only on-policy learning. More robust than GRPO at tiny scale | High after task SFT |
| Distillation: sequence-level KD, on-policy distillation (Thinking Machines, Oct 2025), GKD, MiniPLM (2410.17215), distillation scaling laws (2502.08606) | GPT-2 BPE blocks direct logit KD from Qwen/SmolLM. Cross-tokenizer KD needs ULD (2402.12030) or TRL GOLD | Sequence-level KD (SFT on teacher text): yes. Logit KD: experimental |
| Loop-aware RL: RLTT (2602.10520) spreads GRPO credit over loop iterations; LoopRPT (2603.19714) | RLTT reports +5.8 and +10.9 over GRPO on Ouro-1.4B and 2.6B [abs] | **Most interesting experiment** for the GSM8K RL stage |
| Latent RL: Dropout-GRPO (2606.10184), HRPO (2505.18454), CoLaR (2505.16552), SLPO (2607.19691) | Deterministic latent rollouts kill GRPO's group variance; these methods re-inject stochasticity. About +1–2 points | Experimental, after CODI |
| Learned exit gates (Ouro; TaH2 2609.35748; diagnostics 2607.20519) | Learned gates rarely beat KL-exit at matched compute | Skip. Keep training-free KL exit |
| Checkpoint averaging and WiSE interpolation (2505.12082) | Averaging decay-phase checkpoints approximates annealing. L20-Edu: 0.875·SFT + 0.125·base is slightly better | Cheap. Do it |

**Constraints specific to the looped model**
- Keep the loop-count *distribution* identical across mid-training, SFT and RL. Rollouts and updates must use the same depth, otherwise RL goes off-policy.
- Record the accuracy-versus-loops curve after every stage. Single-depth finetuning can collapse test-time scaling.

**Recommended pipeline (one 4090, about 15–35 GPU-hours after pretraining) [estimates]**

| Stage | What | Expected gain | Time |
|---|---|---|---|
| A. Decay mid-training | Mix in the last 15% of pretraining: 50% web, 15–20% FineMath, 10% Stack-Edu, 10% Cosmopedia, 3–5% QA/instruction. Average the last checkpoints | +2–5 ARC-E / HellaSwag | About free |
| B. General SFT | smol-smoltalk + MMLU-aux + GSM8K, ChatML tokens, assistant-only loss, 1–2 epochs, randomized loops. WiSE-interpolate with base | IFEval 20–30 | 2–5 GPU-h |
| C. Task SFT | GSM8k-Aug explicit CoT, 3–6 epochs. This is `coconut.py` stage 0 and the CODI teacher | 35–45% GSM8K | 3–8 GPU-h |
| D. Rejection-sampling FT | k=16 samples, keep the correct ones, 2 rounds, LR 5e-5 | +2–4 | 2–4 GPU-h |
| E. Dr. GRPO, β=0, G=16 | Only if pass@16 > 30%. LR 1e-6–3e-6, 1–2 epochs; RLTT trajectory credit as the ablation | +1–5 | 4–10 GPU-h |
| F. Coconut/CODI latents | Then optionally Dropout-GRPO on the latents | Same accuracy with ~3× shorter reasoning | 5–10 GPU-h |

**Skip:** RL on the base or general-SFT model, long reasoning-trace SFT, QAT, chasing MMLU (near chance at this size).

---

## 6. Released models that use our techniques (as of Oct 2026)

How this list was checked:
- Configuration and attention code was confirmed in the GitHub source of `huggingface/transformers`, nanochat and modded-nanogpt.
- Hugging Face pages could not be opened from the sandbox, so those links are as found via search.
- **[u]** = confirmed by only one secondary source.

| Technique | Models (newest first) |
|---|---|
| Recurrent depth / looping | [Parcae 140M–1.3B](https://huggingface.co/SandyResearch/parcae-1.3b) (Apr 26) · [Ouro-1.4B](https://huggingface.co/ByteDance/Ouro-1.4B) / [2.6B-Thinking](https://huggingface.co/ByteDance/Ouro-2.6B-Thinking) (Oct 25, `total_ut_steps: 4`) · [MoR 360M](https://github.com/raymin0223/mixture_of_recursions) (Jul 25) · [Huginn-0125 3.5B](https://huggingface.co/tomg-group-umd/huginn-0125) (Feb 25) |
| Gated attention | Qwen3.5 / 3.6 ([blog](https://qwen.ai/blog?id=qwen3.5), Feb–Apr 26) · [Arcee Trinity Large](https://arxiv.org/abs/2602.17004) · [Qwen3-Next-80B-A3B](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) (Sep 25) |
| Linear-attention hybrid | [Qwen3.8-Flash-Next](https://github.com/QwenLM/Qwen3.8-Flash-Next) (Aug 26, GDN + sparse attention) · Kimi K3 ([2607.24653](https://arxiv.org/abs/2607.24653), 3 KDA : 1 MLA) · [Nemotron 3 Nano](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16) (Mamba-2) · [Kimi Linear 48B](https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Instruct) (3 KDA : 1 MLA) · Qwen3-Next (3 GDN : 1 gated attention) · Granite 4.0-H (9 : 1) · Falcon-H1 (parallel) |
| QK-norm | Gemma 4 · [OLMo 3](https://huggingface.co/allenai/Olmo-3-7B-Think) · [Qwen3](https://huggingface.co/Qwen/Qwen3-8B) · Gemma 3 · nanochat |
| Partial RoPE / NoPE | Kimi K3 / Kimi Linear (NoPE in MLA layers) · Gemma 4 (p-RoPE 0.25 on global layers) · Qwen3-Next / 3.5 (0.25) · [GLM-4.5](https://huggingface.co/zai-org/GLM-4.5) (0.5) · [SmolLM3](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) (NoPE every 4th layer) · Llama 4 (iRoPE) |
| Sliding window / global | DeepSeek-V4 (128-token SWA branch) · Gemma 4 / Gemma 3 (5:1) · OLMo 3 (3:1, 4096 window) · [gpt-oss](https://huggingface.co/openai/gpt-oss-120b) (1:1, 128 window, learned sinks) |
| Value residual / value embeddings / XSA | [nanochat](https://github.com/karpathy/nanochat) (gated value embeddings) · [modded-nanogpt](https://github.com/KellerJordan/modded-nanogpt) (value embeddings since #14, XSA at #82). No production LLM yet |
| ReLU² | Nemotron 3 Nano · [Nemotron Nano 2](https://arxiv.org/abs/2508.14444) · [nanochat-d32](https://huggingface.co/karpathy/nanochat-d32) |
| Muon | Qwen3.8-Flash-Next · Kimi K3 (per-head) · DeepSeek-V4 · Trinity · [GLM-4.5](https://arxiv.org/abs/2508.06471) · [Kimi K2](https://huggingface.co/moonshotai/Kimi-K2-Instruct) (MuonClip). Polar Express and NorMuon are used only in the speedrun so far |
| MTP | Qwen3.8-Flash-Next · DeepSeek-V4 · GLM-4.5 → GLM-5 · [DeepSeek-V3](https://huggingface.co/deepseek-ai/DeepSeek-V3) |
| MLA / sparse attention (skipped) | DeepSeek-V4 (CSA / HCA) · [GLM-5](https://github.com/zai-org/GLM-5) (DSA) · DeepSeek-V3.2 (DSA) · DeepSeek-V3 (MLA) |
| Latent reasoning | Research checkpoints only: [internlm/SIM_COT-GPT2-Coconut](https://huggingface.co/internlm/SIM_COT-GPT2-Coconut) · [zen-E CODI](https://huggingface.co/zen-E) · [ModalityDance/slpo-coconut-gpt2](https://huggingface.co/ModalityDance/slpo-coconut-gpt2). Meta has no official Coconut checkpoint |
| Post-training | [OLMo 3 Think](https://huggingface.co/allenai/Olmo-3-7B-Think) (SFT → DPO → RLVR) · [SmolLM3](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) (APO, then merged with a mid-training checkpoint) · Qwen3 small models (strong-to-weak on-policy distillation, [2505.09388](https://arxiv.org/abs/2505.09388)) · [DAPO-Qwen-32B](https://huggingface.co/BytedTsinghua-SIA/DAPO-Qwen-32B) · RLTT / LoopRPT applied to Ouro (papers only, no weights) |

---

## 7. Tool calling and agentic use (Oct 2026)

**Verdict: narrow tool use works at this size; general agents do not.** Evidence from the smallest tool-calling models:

| Model | Size | Result |
|---|---|---|
| FunctionGemma (Google, Dec 2025) | 270M | BFCL Simple 61.6, Relevance 61.1. Mobile Actions 58% → **85% after task finetuning**. Built on Gemma 3's ~6T-token pretraining |
| Octopus v2 | — | 98–99% on its own ~20 Android functions, using one special token per tool (functional tokens) |
| TinyAgent | 1.1B | 80% on its macOS tools, with a tool retriever in front |
| Hammer2.1-0.5B, Qwen3-0.6B | 0.5–0.6B | ~62 BFCL overall, but **multi-turn 3–4%** |
| Toolformer | GPT-2 sizes | Tool *judgment* only emerged at ~775M |
| nanochat d20 (561M, calculator tool) | 561M | GSM8K 2.5 → 4.6 (SFT) → 7.6 (RL) |

**What NanoLoop implements:**
- Single special tokens per tool-use element, with the Hermes/Qwen JSON call body (`<|tool_call|>{"name":…,"arguments":{…}}<|/tool_call|>`).
- Tool responses and calculator outputs are never trained on.
- **Constrained decoding** (`nanoloop/agent.py`): the tool name is restricted to registered tools and the arguments to valid JSON. Arguments that run past their budget are closed deterministically. Every emitted call parses.
- A nanochat-style **inline calculator** (`<|calc|>expr<|/calc|><|out|>result<|/out|>`) for math. The engine injects the result, and RL masks it out of the loss.
- A **ReAct-lite loop** capped at 3 steps. The last step must answer.
- Data:
  - per-tool synthetic data, the most important part (`tools-synth`), with ~15% no-call negatives;
  - `xlam` with 30% Hammer-style name masking;
  - `hermes` and `smoltalk2-tools`.

**Realistic targets:**

| Task | Target |
|---|---|
| Our own finetuned tools | ~90% exact match |
| BFCL simple | 25–45 |
| BFCL irrelevance | 50–70 |
| GSM8K with calculator, SFT then RL | 3–8% |
| Multi-step autonomy | none meaningful |

For real agentic work, use a larger pretrained base (Qwen3-0.6B/1.7B, FunctionGemma), with NanoLoop as a router or classifier in front of it.

**Sources:** FunctionGemma, Octopus v2 (2404.01744), TinyAgent (2409.00608), Hammer (2410.04587), HyFunc (2602.13665), When2Call (2504.18851), ToolRL (2504.13958), Toolformer (2302.04761), nanochat `engine.py` and `tasks/gsm8k.py`.

## 8. Frontier architectures, Oct 2026: what we adopted

Most of this was read from source code (`huggingface/transformers` main and vLLM). Hugging Face pages could not be opened from the sandbox.

| Model | What's new | Adopt at 200M / 2k / 1 GPU? |
|---|---|---|
| **Qwen3.8-Flash-Next** (`qwen4_exp`, "Qwen4 preview"; [paper 2608.30320](https://arxiv.org/abs/2608.30320), [code](https://github.com/huggingface/transformers/tree/main/src/transformers/models/qwen4_exp)) | 3 Gated DeltaNet : 1 **QSA** (block-sparse attention, mean-pooled 4-token keys, ReLU indexer). **GatedResidual** with 4 streams. **PLE** hashed n-gram embeddings. Muon only on true matrices | **GatedResidual: yes** (`hc_streams`). **PLE: yes** (`ngram_memory`). QSA: no, a no-op at 2k |
| **DeepSeek V4 / V4.1-Flash** ([V4 2606.19348](https://arxiv.org/abs/2606.19348), [V4.1 2609.19969](https://arxiv.org/abs/2609.19969)) | CSA/HCA compressed sparse attention (V4.1: CSA2 with cross-layer KV/index reuse). **mHC** (Sinkhorn-mixed hyper-connections). **Engram** n-gram tables. Hash-MoE. MTP | **Engram: yes** (same mechanism as PLE). mHC: maybe, since GatedResidual is the cheaper relative. CSA/MoE: no |
| **GLM-5.3** (post-training on GLM-5.2) / **GLM-5.3-Flash** (`glm5_next`) | DSA + **IndexShare** (one indexer per 4 layers). Flash: KDA:MLA 3:1, NoPE MLA, KPool=16, mHC | No: these pay off beyond ~32k context |
| Kimi K3 | KDA + gated MLA, **Block Attention Residuals** (2603.15031) | Experimental: attention over loop iterations is untested in looped models |
| Gemma 4 | 5:1 sliding window, p-RoPE 0.25 on global layers, K=V, cross-layer KV sharing, per-layer embeddings | Our `loop-swa` preset covers the pattern |
| MiniMax-M3-preview | QK-norm, partial RoPE 64, max-pooled block-sparse attention | Already have QK-norm and partial RoPE |

The new `loop-frontier` preset is `loop-base` plus **Engram/PLE** (2–3-gram, 4 hashes per order, ~51M table parameters, signed-sqrt sigmoid gate, ~zero FLOPs) plus **2-stream GatedResidual**. The optimizer was also tidied: GatedResidual gates and n-gram tables go to AdamW (Qwen3.8 / DeepSeek V4 practice), and Gated DeltaNet uses `A_log ~ log U(0.01, 16)`.

**Expected effect (estimate, not measured):** about −0.02 to −0.04 val loss from Engram, and better high-LR stability from GatedResidual. Run it against `loop-base` at equal tokens.

**Skipped:** QSA, DSA, CSA, IndexShare, KPool (sparse attention only pays at long context), MoE / hash-MoE (we are dense), and MTP (weak at small scale).

## 9. Latent-space reasoning, Oct 2026: moving past Coconut

Coconut + CODI was the frontier in early 2025. Two 2026 shifts:
1. **Every latent gets its own supervision.** SIM-CoT gives +8 over Coconut. Chen et al. (2606.20075) show that answer-only latent training falls to the No-CoT level.
2. **Latents are refined in parallel by a looped backbone** (LOTUS, LLoCoT).

| Method | GPT-2 GSM8K | Larger models |
|---|---|---|
| Coconut | 34.1 | — |
| CODI | ~43.7 | — |
| SIM-CoT + Coconut | ~44.8 | — |
| PCCoT | ~49.5 (uncertain) | — |
| **LOTUS (2606.31779)** | **44.1** (CoT 42.7) | 1B: **57.3**; 3B: 70.0 vs CoT 71.5. The first latent method whose gap to CoT does not grow with scale |

**Implemented: `lotus.py`.**
- The workspace is K=6 blocks × c=13 latent slots. Each slot is a learned base embedding plus a block position plus a slot position.
- The workspace is refined in parallel by NanoLoop's recurrent core, which plays the role of LOTUS's weight-shared refinement loop.
- Every slot is trained to read out its own token of the gold step, with `<|pad-step|>` past the end of the step.
- Optional per-loop deep supervision.
- One forward pass per example, against n+1 sequential passes for Coconut.
- Decoding the slots gives a readable thought trace.
- Evaluation follows the critiques: an accuracy-vs-loops sweep, and a **zero-workspace shortcut test**.

**Critiques that shape the evaluation:**
- 2512.21711: Coconut latents act as placeholders.
- 2602.22441: weakly supervised latents take shortcuts.
- 2604.06374: real superposition shows up only when training from scratch, which is NanoLoop's regime.
- 2605.26733: accuracy can collapse past the best loop depth, so always sweep r.

**Next upgrades:**
- **RLTT** per-loop credit, already in `rl.py --loop-credit all`.
- **SLPO / Dropout-GRPO**, to make latent rollouts stochastic for RL.
- **LLoCoT** (2610.11472, Oct 2026): a probabilistic latent head that makes the latents samplable.

## 10. Long context on a small budget

**Reference point.** LFM2.5-350M ([card](https://huggingface.co/LiquidAI/LFM2.5-350M), [LFM2 report 2511.23404](https://arxiv.org/abs/2511.23404)) reaches 32K context with:
- 16 layers: 10 double-gated short-convolution blocks and only 6 GQA attention blocks;
- **28T** pretraining tokens;
- a long-context stage.

The architecture is what makes 32K cheap; the token budget is what makes it usable. We can copy the architecture, and replace most of the budget with targeted training:

| Lever | Cost | Implementation |
|---|---|---|
| Sequence-length curriculum (512 → 4K) | Saves compute: short early steps are cheaper at equal tokens per step | `train.py --seq-schedule 512:0.1,1024:0.3,2048:0.6,4096:1.0` |
| Constant-state mixers | Same tokens | `loop-long` preset: 3 global attention layers of 8 unique (1 in 4 inside the loop). The rest are LFM2 gated short convs (`C`) and Gated DeltaNet (`D`). 3.3 vs 8.2 GFLOP/token at 32K against loop-base |
| RoPE scaling | Zero for ~2×; short finetune for 4–8× | `--rope-scaling yarn/ntk --rope-factor F` in `sample.py` / `eval_niah.py`. YaRN per 2309.00071, with attention sharpening (0.1 ln s + 1)² |
| Long-context stage | ~100–300M tokens (estimate: 2–4 GPU-hours) | `train.py --init … --seq-len 16384 --set rope_base=500000 --set max_seq_len=32768`, on PG19 books + FineWeb-Edu ≥4K-token docs + synthetic retrieval (Fu et al. 2402.10171; ProLong 2410.02660) |
| Synthetic retrieval data (~5–10% of the stage) | Free (generated locally) | `prepare_data.py synth-retrieval`: needles and key-value lookups in real web text (2406.19292) |
| Measure usable context | — | `eval_niah.py`: needle grid (held-out words) plus loss by position |

**Expected result:** about 16–32K context that is affordable to train and run, with dependable retrieval up to roughly 8K and degrading beyond that. These are estimates to confirm with `eval_niah.py`. Checkpoints now record `context_len` (the trained length), and the agent budgets prompts against it rather than the RoPE table size.
