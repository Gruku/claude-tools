"""Weight-space merging of NanoLoop checkpoints (same architecture).

  # WiSE-FT style interpolation of a finetune with its base (L20-Edu found 0.875/0.125 best;
  # SmolLM3 merges its APO model with a mid-training checkpoint the same way):
  python merge.py runs/sft/ckpt_final.pt runs/base/ckpt_final_avg.pt --weights 0.875,0.125 --out runs/sft/wise.pt
  # uniform checkpoint soup:
  python merge.py a.pt b.pt c.pt --out soup.pt
"""

from __future__ import annotations

import argparse

import torch


def merge_state_dicts(states, weights):
    total = sum(weights)
    out = {}
    for k in states[0]:
        out[k] = sum(w / total * s[k].float() for s, w in zip(states, weights))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpts", nargs="+")
    ap.add_argument("--weights", default=None, help="comma list (default: uniform)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cks = [torch.load(p, map_location="cpu", weights_only=False) for p in a.ckpts]
    configs = [c["config"] for c in cks]
    if any(c != configs[0] for c in configs):
        raise SystemExit("checkpoints have different model configs; cannot merge")
    weights = [float(w) for w in a.weights.split(",")] if a.weights else [1.0] * len(cks)
    states = [{k.replace("._orig_mod", ""): v for k, v in c["model"].items()} for c in cks]
    merged = merge_state_dicts(states, weights)
    torch.save(dict(model=merged, config=configs[0], chat_init=any(c.get("chat_init") for c in cks),
                    merged_from=list(zip(a.ckpts, weights))), a.out)
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
