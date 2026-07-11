"""Thin FastMCP adapter for the Agent Relay Node CLI."""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from fastmcp import FastMCP


PLUGIN_ROOT = Path(__file__).resolve().parent
NODE = shutil.which("node")
CLI = PLUGIN_ROOT / "scripts" / "agent-relay.js"
STATE_ROOT = Path(
    os.environ.get("LOCALAPPDATA")
    or os.environ.get("XDG_STATE_HOME")
    or (Path.home() / ".local" / "state")
)
PROFILE = STATE_ROOT / "agent-relay" / "mcp-sessions" / f"{uuid.uuid4()}.json"
DATABASE = Path(os.environ.get("AGENT_RELAY_DATABASE", STATE_ROOT / "agent-relay" / "relay.sqlite"))


@atexit.register
def _remove_process_credentials() -> None:
    """Remove the MCP process credential file; the broker expires stale sessions by TTL."""
    PROFILE.unlink(missing_ok=True)

mcp = FastMCP(
    "Agent Relay",
    instructions=(
        "Join only when the user explicitly asks this chat to participate. "
        "Use direct requests for bounded reviews and inbox to receive messages."
    ),
)


def _run(command: str, **options: object) -> object:
    if NODE is None:
        raise RuntimeError("Agent Relay requires Node.js 22.5 or newer")
    argv = [
        NODE,
        str(CLI),
        command,
        "--profile",
        str(PROFILE),
        "--database",
        str(DATABASE),
    ]
    for name, value in options.items():
        if value is None:
            continue
        argv.extend([f"--{name.replace('_', '-')}", str(value)])
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "relay command failed"
        raise RuntimeError(message)
    return json.loads(completed.stdout)


@mcp.tool
def agent_relay_status() -> object:
    """Report whether this chat uses a local database or the cross-OS broker."""
    url = os.environ.get("AGENT_RELAY_URL")
    return {
        "transport": "http-broker" if url else "local-sqlite",
        "url": url,
        "configured": bool(url and os.environ.get("AGENT_RELAY_TOKEN")) if url else True,
        "joined": PROFILE.exists(),
    }


@mcp.tool
def agent_relay_join(label: str, host: str, rooms: list[str] | None = None) -> object:
    """Explicitly join this MCP-backed CLI chat to Agent Relay."""
    if PROFILE.exists():
        raise RuntimeError("This CLI chat already joined Agent Relay; leave before joining again")
    return _run("join", label=label, host=host, rooms=",".join(rooms) if rooms else None)


@mcp.tool
def agent_relay_who() -> object:
    """List active sessions after this CLI chat has joined."""
    return _run("who")


@mcp.tool
def agent_relay_send(body: str, to_session_id: str | None = None, room: str | None = None) -> object:
    """Send one direct or room message from this joined CLI chat."""
    return _run("send", body=body, to=to_session_id, room=room)


@mcp.tool
def agent_relay_request(to_session_id: str, body: str) -> object:
    """Send a bounded work or adversarial-review request to one active session."""
    return _run("request", to=to_session_id, body=body)


@mcp.tool
def agent_relay_reply(request_id: str, body: str) -> object:
    """Reply to a request addressed to this joined CLI chat."""
    return _run("reply", request=request_id, body=body)


@mcp.tool
def agent_relay_inbox(after_sequence: int = 0, limit: int = 100) -> object:
    """Read direct and joined-room messages for this CLI chat."""
    return _run("inbox", after=after_sequence, limit=limit)


@mcp.tool
def agent_relay_leave() -> object:
    """Disconnect this CLI chat and invalidate its relay credentials."""
    result = _run("leave")
    PROFILE.unlink(missing_ok=True)
    return result


if __name__ == "__main__":
    mcp.run()
