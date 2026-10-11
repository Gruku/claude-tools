"""NanoLoop: a GPT-2-sized recurrent-depth language model built from 2025-26 research."""

from .config import ModelConfig, make_config, PRESETS
from .model import NanoLoop

__all__ = ["ModelConfig", "make_config", "PRESETS", "NanoLoop"]
