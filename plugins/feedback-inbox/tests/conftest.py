# plugins/feedback-inbox/tests/conftest.py
"""Shared pytest fixtures for feedback-inbox tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Make `from scripts.resolve_target import ...` work from anywhere.
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
