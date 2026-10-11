"""Sample from a trained checkpoint. The loop count is a test-time compute dial.

  python sample.py runs/<run>/ckpt_final.pt --prompt "The meaning of life is" --steps 8
  python sample.py ckpt.pt --prompt "..." --steps 32 --exit-threshold 1e-3   # adaptive depth
  python sample.py runs/sft/wise.pt --chat "Why is the sky blue?"            # post-trained model
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext

import torch

from nanoloop.chat import decode, render_prompt
from nanoloop.checkpoint import gpt2_tokenizer, load_model
from nanoloop.config import END_TURN


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--prompt", default="The history of the Roman Empire")
    ap.add_argument("--chat", default=None, help="user message, rendered in the chat template")
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--steps", type=int, default=None, help="loop budget per token (default: training mean)")
    ap.add_argument("--exit-threshold", type=float, default=None, help="adaptive exit (KL or latent delta)")
    ap.add_argument("--exit-criterion", choices=["kl", "latent"], default="kl")
    ap.add_argument("--num-samples", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    model = load_model(a.ckpt, a.device)
    enc = gpt2_tokenizer()
    if a.chat:
        prompt = render_prompt(enc, [dict(role="user", content=a.chat)])
        stop = END_TURN
    else:
        prompt = [enc.eot_token] + enc.encode(a.prompt)
        stop = enc.eot_token
    idx = torch.tensor([prompt] * a.num_samples, device=a.device)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if a.device.startswith("cuda") else nullcontext()
    with amp:
        out, steps = model.generate(idx, a.max_new_tokens, temperature=a.temperature, top_k=a.top_k,
                                    num_steps=a.steps, exit_threshold=a.exit_threshold,
                                    exit_criterion=a.exit_criterion, eos_token=stop)
    for row in out.tolist():
        print("-" * 80)
        print(decode(enc, row[len(prompt):] if a.chat else row[1:]))
    if steps:
        print("-" * 80)
        print(f"loops/token: mean {sum(steps) / len(steps):.2f}, min {min(steps)}, max {max(steps)}")


if __name__ == "__main__":
    main()
