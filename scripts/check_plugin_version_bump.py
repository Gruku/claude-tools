"""check_plugin_version_bump.py — verify plugin versions are in sync and bumped.

The "relevant parts" of a plugin version live in up to three places that must
move together for a release to register cleanly:

  1. plugins/<name>/.claude-plugin/plugin.json   -> "version"
  2. .claude-plugin/marketplace.json             -> plugins[name].version
  3. plugins/<name>/CHANGELOG.md                 -> a "## <version>" entry
     (only plugins that ship a CHANGELOG.md are held to this)

This script is the canonical pre-PR checker. The push-time guard hook
(.claude/hooks/check-version-bump.sh) is a leaner bash backstop; this is the
richer, manually-runnable check that the PR workflow should call.

Usage:
  python scripts/check_plugin_version_bump.py                 # sync-check all plugins
  python scripts/check_plugin_version_bump.py taskmaster      # one plugin
  python scripts/check_plugin_version_bump.py --base origin/master
        # additionally require: any plugin whose source changed vs <base>
        # must have a bumped version, and (if it has one) a CHANGELOG entry
        # for the new version.

Exit code: 0 = all good, 1 = one or more problems reported.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


def _load_marketplace_versions() -> dict[str, str]:
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in data.get("plugins", []):
        name = entry.get("name")
        if name:
            out[name] = entry.get("version", "")
    return out


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd or ROOT), *args],
        capture_output=True, text=True,
    ).stdout.strip()


def _submodule_sha(name: str, ref: str) -> str | None:
    """Gitlink SHA of plugins/<name> at superproject <ref>, or None if the
    path is not a submodule there (regular dir, or doesn't exist)."""
    line = _git("ls-tree", ref, "--", f"plugins/{name}")
    if not line or not line.startswith("160000"):
        return None
    return _git("rev-parse", f"{ref}:plugins/{name}") or None

def _submodule_file(name: str, sha: str, rel: str) -> str | None:
    """Contents of <rel> inside the plugins/<name> submodule at commit <sha>."""
    blob = _git("show", f"{sha}:{rel}", cwd=ROOT / "plugins" / name)
    return blob or None


def _plugin_json_version(name: str) -> str | None:
    # Submodule plugins: read through the gitlink at HEAD, not the working
    # dir — a lagging `git submodule update` must not skew the check.
    sha = _submodule_sha(name, "HEAD")
    if sha:
        blob = _submodule_file(name, sha, ".claude-plugin/plugin.json")
        if blob:
            try:
                return json.loads(blob).get("version")
            except json.JSONDecodeError:
                return None
    pjson = ROOT / "plugins" / name / ".claude-plugin" / "plugin.json"
    if not pjson.exists():
        return None
    return json.loads(pjson.read_text(encoding="utf-8")).get("version")


def _changelog_has(name: str, version: str) -> bool | None:
    """True/False if a CHANGELOG exists; None if the plugin has no CHANGELOG."""
    sha = _submodule_sha(name, "HEAD")
    if sha:
        text = _submodule_file(name, sha, "CHANGELOG.md")
        if text is None:
            return None
    else:
        changelog = ROOT / "plugins" / name / "CHANGELOG.md"
        if not changelog.exists():
            return None
        text = changelog.read_text(encoding="utf-8")
    # Match a heading line like "## 3.9.0" or "## 3.9.0 — title".
    return re.search(rf"^##\s+{re.escape(version)}\b", text, re.MULTILINE) is not None


def _plugins_changed_since(base: str) -> set[str]:
    changed = _git("diff", "--name-only", f"{base}...HEAD")
    names: set[str] = set()
    for line in changed.splitlines():
        parts = line.split("/")
        if len(parts) >= 2 and parts[0] == "plugins" and not parts[1].startswith(("_", ".")):
            names.add(parts[1])
    return names


def _version_at(base: str, name: str) -> str | None:
    # Submodule plugins: `git show base:plugins/<name>/...` cannot traverse a
    # gitlink, so resolve the gitlink SHA at <base> and read inside the
    # submodule (B-074: this silent skip let unbumped submodule advances pass).
    sha = _submodule_sha(name, base)
    if sha:
        blob = _submodule_file(name, sha, ".claude-plugin/plugin.json")
    else:
        blob = _git("show", f"{base}:plugins/{name}/.claude-plugin/plugin.json")
    if not blob:
        return None
    try:
        return json.loads(blob).get("version")
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plugin", nargs="?", help="check only this plugin")
    ap.add_argument("--base", help="git ref; require a bump for plugins changed since it")
    args = ap.parse_args()

    mp = _load_marketplace_versions()
    targets = [args.plugin] if args.plugin else sorted(mp)
    changed = _plugins_changed_since(args.base) if args.base else set()

    problems: list[str] = []
    for name in targets:
        pj = _plugin_json_version(name)
        if pj is None:
            problems.append(f"{name}: no plugins/{name}/.claude-plugin/plugin.json")
            continue
        mpv = mp.get(name)
        if mpv is None:
            problems.append(f"{name}: not listed in marketplace.json")
        elif pj != mpv:
            problems.append(
                f"{name}: OUT OF SYNC — plugin.json v{pj} vs marketplace.json v{mpv}"
            )

        if args.base and name in changed:
            old = _version_at(args.base, name)
            if old is not None and old == pj:
                problems.append(
                    f"{name}: source changed since {args.base} but version still v{pj} (NOT bumped)"
                )
            elif _changelog_has(name, pj) is False:
                problems.append(
                    f"{name}: v{pj} bumped but CHANGELOG.md has no '## {pj}' entry"
                )

    if problems:
        print("Plugin version check FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1

    scope = args.plugin or "all plugins"
    print(f"Plugin version check OK ({scope}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
