"""Load a trained NanoLoop from any nanoloop checkpoint (train / sft / rl / merge)."""

from __future__ import annotations

import torch

from .config import ModelConfig
from .model import NanoLoop


def load_checkpoint(path: str, device: str = "cpu"):
    """Returns (model in eval mode, raw checkpoint dict)."""
    ck = torch.load(path, map_location=device, weights_only=False)
    model = NanoLoop(ModelConfig(**ck["config"])).to(device)
    state = {k.replace("._orig_mod", ""): v for k, v in ck["model"].items()}
    model.load_state_dict(state)
    model.eval()
    return model, ck


def load_model(path: str, device: str = "cpu") -> NanoLoop:
    return load_checkpoint(path, device)[0]


def save_checkpoint(path: str, model, **extra):
    torch.save(dict(model=model.state_dict(), config=model.cfg.to_dict(), **extra), path)


def gpt2_tokenizer():
    import tiktoken
    return tiktoken.get_encoding("gpt2")
