from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.resolve_target import resolve_target


def _write_config(home: Path, payload: dict) -> Path:
    cfg_dir = home / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "inbox-target.json"
    cfg.write_text(json.dumps(payload), encoding="utf-8")
    return cfg


def test_missing_config_returns_disabled_with_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows fallback
    r = resolve_target()
    assert r.enabled is False
    assert r.inbox is None
    assert r.reason is not None and "not configured" in r.reason.lower()


def test_disabled_flag_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    _write_config(tmp_path, {"inbox": str(tmp_path / "inbox"), "enabled": False})
    r = resolve_target()
    assert r.enabled is False
    assert "disabled" in r.reason.lower()


def test_valid_config_resolves_and_creates_inbox(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    inbox_path = tmp_path / "inbox"
    _write_config(tmp_path, {"inbox": str(inbox_path), "enabled": True})
    r = resolve_target()
    assert r.enabled is True
    assert r.inbox == inbox_path
    assert inbox_path.is_dir()
    assert r.reason is None


def test_malformed_json_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    cfg_dir = tmp_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "inbox-target.json").write_text("{not json", encoding="utf-8")
    r = resolve_target()
    assert r.enabled is False
    assert "parse" in r.reason.lower() or "invalid" in r.reason.lower()


def test_missing_inbox_key_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    _write_config(tmp_path, {"enabled": True})
    r = resolve_target()
    assert r.enabled is False
    assert "inbox" in r.reason.lower()
