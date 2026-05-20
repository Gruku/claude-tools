"""One-off migration: audit ISS-* entries against the new Issue bar, materialize
on-disk files for stays (backfilling `evidence:`), and demote non-qualifiers to Bugs.

This repo's ISS-* entries currently live only as index entries in backlog.yaml —
no on-disk .taskmaster/issues/ISS-*.md files exist. We materialize the stays as
the canonical source of truth (so future MCP calls don't blow up), and convert
demotes straight to bugs/B-NNN.md.

Usage: python scripts/migrate_iss_to_bug.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the plugin importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "plugins" / "taskmaster"))

import yaml

from taskmaster_v3 import (
    _validate_issue,
    bug_dir,
    issue_dir,
    issue_path,
    next_bug_id,
    sync_bug_index,
    sync_issue_index,
    update_bug,
    write_bug,
    write_task_file,
)

BP = ROOT / ".taskmaster" / "backlog.yaml"

# Per-ISS verdicts after applying the bar (recurring / systemic / outstanding).
# evidence sentence for STAYs MUST cite a concrete criterion.
STAYS: dict[str, str] = {
    "ISS-004": (
        "Systemic: same defect class (Path() literal vs backlog_path.parent) "
        "spans handover writer plus handover/lesson/issue readers — affects "
        "the taskmaster MCP, the v3 file layout, and the viewer reads."
    ),
}

# DEMOTE map: ISS id → migration body note (appended to bug body, optional)
DEMOTES: list[str] = [
    "ISS-005",
    "ISS-006",
    "ISS-007",
    "ISS-008",
    "ISS-009",
    "ISS-010",
    "ISS-011",
    "ISS-012",
    "ISS-013",
    "ISS-014",
    "ISS-015",
]

# Map source status → bug status. wontfix/duplicate collapse to shelved.
STATUS_MAP = {
    "open": "open",
    "investigating": "open",
    "fixed": "fixed",
    "wontfix": "shelved",
    "duplicate": "shelved",
}


def load_backlog() -> dict:
    return yaml.safe_load(BP.read_text(encoding="utf-8")) or {}


def save_backlog(data: dict) -> None:
    BP.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def find_iss_entry(data: dict, iid: str) -> dict | None:
    for e in data.get("issues") or []:
        if e.get("id") == iid:
            return e
    return None


def materialize_stay(data: dict, iid: str, evidence: str) -> Path:
    """Create an on-disk ISS-NNN.md from its backlog.yaml entry, with evidence."""
    entry = find_iss_entry(data, iid)
    if entry is None:
        raise RuntimeError(f"{iid} not found in backlog.yaml")

    # Build full frontmatter — backlog entries are slim; fill required fields.
    fm = {
        "id": iid,
        "title": entry["title"],
        "status": entry.get("status", "open"),
        "severity": entry.get("severity", "P2"),
        "components": entry.get("components") or [],
        "impact": "",
        "evidence": evidence,
        "location": [],
        "discovered": "2026-04-01T00:00:00Z",  # backfilled — original date unknown
        "discovered_by": "user",
        "resolved": None,
        "related_tasks": entry.get("related_tasks") or [],
        "fixed_in_task": None,
        "duplicate_of": None,
        "promoted_from": [],
        "tldr": "",
    }
    if fm["status"] == "fixed":
        # ISS-004 is investigating, not fixed; this branch shouldn't trigger today.
        # Defensive: require a fixed_in_task for fixed status.
        rt = fm["related_tasks"]
        fm["fixed_in_task"] = rt[0] if rt else "unknown"
    _validate_issue(fm)
    p = issue_path(BP, iid)
    write_task_file(p, fm, body="")
    return p


def demote(data: dict, iid: str) -> str:
    """Convert one ISS to a Bug. Returns new bug id."""
    entry = find_iss_entry(data, iid)
    if entry is None:
        raise RuntimeError(f"{iid} not found in backlog.yaml")

    src_status = entry.get("status", "open")
    new_status = STATUS_MAP.get(src_status, "open")

    body = (
        f"_Migrated from {iid} during the bug-tier audit "
        f"(2026-05-20). Original ISS status: {src_status}._\n"
    )

    severity = entry.get("severity") if new_status != "shelved" else None
    components = entry.get("components") or []

    # write_bug always starts at status=open; transition after for fixed/shelved.
    bug_id, _ = write_bug(
        BP,
        title=entry["title"],
        found_in=None,
        discovered_by="user",
        severity=severity,
        components=components,
        location=[],
        body=body,
        status="open",
    )

    if new_status == "fixed":
        # fixed bugs need fix_commit; we don't have one for these legacy ISS — use marker.
        update_bug(BP, bug_id, status="fixed", fix_commit="migrated-no-sha")
    elif new_status == "shelved":
        update_bug(BP, bug_id, status="shelved")

    return bug_id


def main() -> None:
    data = load_backlog()

    # Materialize STAYS first
    print("=== STAYS ===")
    for iid, evidence in STAYS.items():
        p = materialize_stay(data, iid, evidence)
        print(f"  materialized {iid} -> {p.relative_to(ROOT)}")

    # Demote the rest
    print("=== DEMOTES ===")
    mapping: dict[str, str] = {}
    for iid in DEMOTES:
        bid = demote(data, iid)
        mapping[iid] = bid
        # Remove the original ISS entry from backlog.yaml (sync will rebuild)
        data["issues"] = [e for e in (data.get("issues") or []) if e.get("id") != iid]
        print(f"  demoted {iid} -> {bid}")

    # Rebuild indices from disk so backlog.yaml matches reality.
    sync_issue_index(data, BP)
    sync_bug_index(data, BP)
    save_backlog(data)

    print("\n=== MAPPING ===")
    for iid, bid in mapping.items():
        print(f"  {iid} -> {bid}")


if __name__ == "__main__":
    main()
