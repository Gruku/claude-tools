# Where to download the data

This guide covers every NanoLoop stage, with exact commands, sizes and licenses. It was compiled on 2026-10-11 from GitHub sources (nanochat, modded-nanogpt) and Hugging Face dataset cards (seen through search).

Before each large download, run `hf datasets info <id>` or open the card on huggingface.co. That confirms the size, the license and whether the dataset is gated. Items marked **(check)** could not be fully verified from here.

## 0. Setup (Windows: do this inside WSL2)

```bash
# keep data on the Linux filesystem (ext4), NOT /mnt/c — 9P/NTFS is many times slower
export HF_HOME=~/data/hf                 # cache + token location
pip install -U "huggingface_hub[cli]" datasets tiktoken pyarrow
hf auth login                            # or: export HF_TOKEN=hf_...
export HF_XET_HIGH_PERFORMANCE=1         # hf_xet is the default backend; this is the speed switch
# flaky link stalling? export HF_HUB_DISABLE_XET=1
```

- **CLI changes.** `hf` replaces the deprecated `huggingface-cli`, which still works on older versions with the same flags. `HF_HUB_ENABLE_HF_TRANSFER` is ignored in huggingface_hub v1.x.
- **Resuming.** Re-running a `hf download` command skips finished files and resumes partial ones.
- **Gated datasets** (marked 🔒 below). Accept the terms once on the website while logged in.
- **Disk.**
  - NanoLoop token shards take 2 bytes per token (10B tokens ≈ 20 GB).
  - Raw parquet takes about 2.5–3 bytes per GPT-2 token.
  - Tokenize, then delete the parquet. `prepare_data.py` streams, so the parquet never has to be stored.
- **WSL2 storage.** If the WSL2 virtual disk grows too large on C:, move the distro with `wsl --export` / `wsl --import`, or mount a dedicated disk with `wsl --mount`.

## 1. Pretraining (target 2.5–10B tokens)

| Dataset | Id / subset | Size | License | Notes |
|---|---|---|---|---|
| **FineWeb-Edu** (default) | `HuggingFaceFW/fineweb-edu`, `sample-10BT` (also `sample-100BT`, `sample-350BT`) | 10BT = 28.5 GB parquet, ~20 GB as shards | ODC-By | Best fully open choice |
| ClimbMix (nanochat repack) | `karpathy/climbmix-400b-shuffle`, files `shard_00000…06542.parquet`, ~60M tokens each; the last shard is the val split | 170 shards ≈ 10B tokens ≈ 17 GB | CC-BY-NC-4.0 **(check)**, non-commercial | Best measured by nanochat |
| FineWeb, pre-tokenized | `kjj0/fineweb10B-gpt2`: `fineweb_val_000000.bin` + `fineweb_train_000001…000103.bin` | 100M tokens / ~200 MB per shard | ODC-By | Zero tokenization; **use the val shard for the 3.28 GPT-2 benchmark** |
| DCLM-baseline | `mlfoundations/dclm-baseline-1.0-parquet` | multi-TB | CC-BY-4.0 | Slice only, as a mixing partner |
| Nemotron-CC v2 🔒 | `nvidia/Nemotron-CC-v2` | 6.6T tokens | NVIDIA data agreement | Optional high-quality slice |
| Ultra-FineWeb | `openbmb/Ultra-FineWeb` (English: `data/ultrafineweb_en_v1_4/`) | ~1T tokens | **(check)** | Alternative to FineWeb-Edu |

```bash
cd nanoloop
python prepare_data.py fineweb10B --train-shards 1        # val shard (+1 train shard) for the 3.28 benchmark
python prepare_data.py fineweb-edu --max-tokens 5e9       # streams + tokenizes -> data/fineweb-edu/ (~10 GB)
# or ClimbMix (non-commercial):  python prepare_data.py climbmix --max-tokens 5e9
# Tokenize-free fast start:      python prepare_data.py fineweb10B --train-shards 103   (~21 GB)
```

## 2. Mid-training / decay mix (~0.5–1.5B tokens, stage A)

| Dataset | Id / config | Size | License |
|---|---|---|---|
| FineMath | `HuggingFaceTB/finemath`, `finemath-4plus` (9.6B tokens; also `finemath-3plus`, `infiwebmath-4plus`) | ~25 GB | ODC-By |
| Cosmopedia v2 | `HuggingFaceTB/smollm-corpus`, `cosmopedia-v2` (28B tokens, **122 GB** if fully downloaded; stream instead) | — | ODC-By |
| Python-Edu / Stack-Edu | `HuggingFaceTB/smollm-corpus` `python-edu`, `HuggingFaceTB/stack-edu` `Python` | ~4B / ~125B tokens | Ids only; content comes from the Software Heritage S3 bucket (snippet below) |
| OpenWebMath / MegaMath | `open-web-math/open-web-math`, `LLM360/MegaMath` | 14.7B / 370B tokens | ODC-By **(check)** |
| Code without S3 | `codeparrot/codeparrot-clean` (column `content`), `bigcode/the-stack-smol` 🔒 | small | **(check)** |

```bash
python prepare_data.py finemath --max-tokens 5e8
python prepare_data.py cosmopedia-v2 --max-tokens 2e8
python prepare_data.py chat-mix          # smol-smoltalk + GSM8k-Aug + MMLU-aux rendered in the chat template
python prepare_data.py hf --hf-dataset codeparrot/codeparrot-clean --text-column content --name code --max-tokens 2e8
```

Fetching Stack-Edu or python-edu content (unsigned S3 access, slow from home; take a few hundred million tokens at most):

```python
import boto3, gzip
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
text = gzip.decompress(s3.get_object(Bucket="softwareheritage", Key=f"content/{blob_id}")["Body"].read()).decode("utf-8", "replace")
```

## 3. SFT / chat (stages B and C)

Download everything here (a few GB in total). `sft.py` loads these automatically by source name.

| Source name | Dataset | Rows | License |
|---|---|---|---|
| `smoltalk` | `HuggingFaceTB/smol-smoltalk` (`messages`) | 460K train / 24K test | Apache-2.0 |
| `mmlu` | `cais/mmlu`, config `all`, split `auxiliary_train` | ~100K | MIT |
| `gsm8k`, `gsm8k-calc` | `openai/gsm8k`, `main` | 7.5K / 1.3K | MIT |
| `gsm8k-aug`, `gsm8k-aug-calc` | `whynlp/gsm8k-aug` (`question`, `steps`, `answer`) | ~385K | **(check)** |
| (optional) | `allenai/tulu-3-sft-mixture`, `allenai/Dolci-Instruct-SFT-7B`, `HuggingFaceTB/smoltalk2` (`SFT`) | 0.9M / 2.2M | ODC-BY (some subsets NC) |

## 4. Tool calling (stage T)

| Source name | Dataset | Rows | Access |
|---|---|---|---|
| `tools-synth` | generated locally for the built-in tools (`nanoloop/tool_data.py`), including no-call negatives | 20K | no download |
| `xlam` | `Salesforce/xlam-function-calling-60k` 🔒 (`query`, `tools`, `answers`) | 60K | accept terms; CC-BY-4.0 |
| `hermes` | `NousResearch/hermes-function-calling-v1` (`func-calling-singleturn.json`, `func-calling.json`) | ~9K | Apache-2.0 |
| `smoltalk2-tools` | `HuggingFaceTB/smoltalk2`, `SFT` splits `xlam_traces_no_think`, `hermes_function_calling_v1_no_think` | ~10K+ | **(check)** |
| (optional) | `nvidia/When2Call` (when to call vs ask vs refuse), `Team-ACE/ToolACE`, `glaiveai/glaive-function-calling-v2` | 10–113K | **(check)** |
| eval | `pip install bfcl-eval==2025.12.17` (data ships inside the package) | — | Apache-2.0 |

## 5. Preference and RL

- **RL prompts:** GSM8K train (loaded automatically by `rl.py`).
- **Toy RL environment:** `Jiayi-Pan/Countdown-Tasks-3to4` (`target`, `nums`).
- **Preference data (for later APO/SimPO):** `HuggingFaceH4/ultrafeedback_binarized`, splits `train_prefs` / `test_prefs`, ~61K pairs, MIT.
- **MATH:** `EleutherAI/hendrycks_math` (the original `hendrycks/competition_math` was taken down). Too hard at this size.

## 6. Evaluations

| What | Where |
|---|---|
| HellaSwag (used by `eval_hellaswag.py`) | `https://raw.githubusercontent.com/rowanz/hellaswag/master/data/hellaswag_val.jsonl` (downloaded automatically) |
| nanochat CORE bundle (HellaSwag, ARC, PIQA, Winogrande, …) | `curl -LO https://karpathy-public.s3.us-west-2.amazonaws.com/eval_bundle.zip && unzip eval_bundle.zip` |
| ARC | `allenai/ai2_arc`, `ARC-Easy` / `ARC-Challenge` |
| MMLU | `cais/mmlu`, `all`, split `test` |
| GSM8K | `openai/gsm8k` `main` test (used by `eval_gsm8k.py`) |
| IFEval | `google/IFEval` (541 prompts; scoring needs the `lm-eval` checker) |
| BFCL | `bfcl-eval` package; at this size run `simple`, `multiple`, `irrelevance`, `live_simple` |

## 7. Minimal download list (in order)

| # | What | Disk (peak → kept) |
|---|---|---|
| 1 | FineWeb val shard + HellaSwag (+ CORE bundle) | 0.5 GB |
| 2 | FineWeb-Edu `sample-10BT`, streamed and tokenized to 5–10B tokens | → 10–20 GB |
| 3 | Decay mix: finemath 0.5B + cosmopedia 0.2B + chat-mix tokens | → ~2 GB |
| 4 | SFT: smol-smoltalk, cais/mmlu, openai/gsm8k, whynlp/gsm8k-aug | ~2 GB |
| 5 | Tools: accept xLAM terms; hermes FC; (smoltalk2 tool splits) | ~1 GB |
| 6 | Evals: ARC, IFEval, `bfcl-eval` | < 1 GB |

**Disk, steady state:** about 25–45 GB of data. Checkpoints add about 2.6 GB each with optimizer state (217M parameters). A 0.5 TB disk is plenty.
