"""Load a trained NanoLoop from a train.py checkpoint."""

from __future__ import annotations

import torch

from .config import ModelConfig
from .model import NanoLoop


def load_model(path: str, device: str = "cpu") -> NanoLoop:
    ck = torch.load(path, map_location=device, weights_only=False)
    model = NanoLoop(ModelConfig(**ck["config"])).to(device)
    state = {k.replace("._orig_mod", ""): v for k, v in ck["model"].items()}
    model.load_state_dict(state)
    model.eval()
    return model


def gpt2_tokenizer():
    import tiktoken
    return tiktoken.get_encoding("gpt2")
