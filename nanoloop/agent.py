"""Chat with a post-trained NanoLoop that can call tools.

  python agent.py runs/tools/ckpt_final.pt                    # interactive, built-in tools
  python agent.py ckpt.pt --once "Convert 5 km to mi"         # single question
  python agent.py ckpt.pt --steps 12 --max-agent-steps 3      # more loops per token

Built-in tools live in nanoloop/tools.py (calculator, convert_units, word_count).
To add your own: define a Tool with a Python function, add it to the registry
below, and finetune on ~500-1000 examples of it (see tool_data.py `tools-synth`
for the template). Expect reliable single calls on familiar phrasing, not
open-ended multi-step agency, at this model size.
"""

from __future__ import annotations

import argparse
import json
from contextlib import nullcontext

import torch

from nanoloop.agent import run_agent
from nanoloop.checkpoint import gpt2_tokenizer, load_model
from nanoloop.tools import BUILTIN_TOOLS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ckpt")
    ap.add_argument("--once", default=None)
    ap.add_argument("--steps", type=int, default=None, help="core loops per token")
    ap.add_argument("--max-agent-steps", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--no-tools", action="store_true")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    model = load_model(a.ckpt, a.device)
    enc = gpt2_tokenizer()
    tools = {} if a.no_tools else dict(BUILTIN_TOOLS)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if a.device.startswith("cuda") else nullcontext()
    history = [dict(role="system", content="", tools=list(tools.values()) or None)]

    def show(kind, payload):
        if kind == "tool":
            print(f"  [tool] {json.dumps(payload['call'])} -> {payload['result']}")
        elif payload["calls"]:
            if payload["text"]:
                print(f"  [thinking] {payload['text']}")
        else:
            print(f"assistant: {payload['text']}")

    while True:
        q = a.once or input("you: ").strip()
        if not q:
            continue
        history.append(dict(role="user", content=q))
        with amp:
            history = run_agent(model, enc, history, tools, max_steps=a.max_agent_steps,
                                num_steps=a.steps, temperature=a.temperature, on_event=show)
        if a.once:
            break


if __name__ == "__main__":
    main()
