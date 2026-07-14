"""Build the regular-file Taskmaster payload consumed by Codex marketplace installs.

The canonical Taskmaster source remains the plugins/taskmaster submodule. Codex's
repository marketplace checkout does not materialize submodules, so its catalog
entry points at the generated codex-plugins/taskmaster snapshot instead.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "plugins" / "taskmaster"
DESTINATION = ROOT / "codex-plugins" / "taskmaster"

DIRECTORIES = (
    ".codex-plugin",
    "playbooks",
    "skills",
    "taskmaster",
    "viewer/css",
    "viewer/js",
    "viewer/vendor",
)

FILES = (
    "backlog_server.py",
    "viewer/index.html",
)

IGNORED_NAMES = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def ignore_generated(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORED_NAMES or Path(name).suffix in IGNORED_SUFFIXES
    }


def copy_distribution() -> None:
    if not (SOURCE / ".codex-plugin" / "plugin.json").is_file():
        raise SystemExit("Taskmaster submodule is missing its Codex plugin manifest")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir(parents=True)

    for relative in DIRECTORIES:
        source = SOURCE / relative
        destination = DESTINATION / relative
        shutil.copytree(source, destination, ignore=ignore_generated)

    for relative in FILES:
        destination = DESTINATION / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / relative, destination)

    # Keep generated additions clean under `git diff --check` even when an
    # upstream text file carries extra blank lines at EOF.
    store_js = DESTINATION / "viewer" / "js" / "store.js"
    store_js.write_text(
        store_js.read_text(encoding="utf-8").rstrip() + "\n",
        encoding="utf-8",
    )

    commit = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={SOURCE.as_posix()}",
            "-C",
            str(SOURCE),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = json.loads(
        (SOURCE / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    metadata = {
        "generated_from": "plugins/taskmaster",
        "upstream_commit": commit,
        "version": manifest["version"],
    }
    (DESTINATION / ".taskmaster-distribution.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    copy_distribution()
