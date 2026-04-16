"""MCPBridge HTTP client for the ue5-materials plugin.

Talks to the MCPBridge UE5 editor plugin at http://localhost:13580/mcp.
Own session cache — no dependency on LF-assist.

=== MCPBridge session lifecycle (IMPORTANT) ===

MCPBridge mints `Mcp-Session-Id` ONCE, on the very first `initialize` call
after Editor startup. Subsequent initializes succeed but do not re-emit the
header, and once the session is lost (cache deleted, stale, or consumed by
another client) the only recovery is an Editor restart followed by a fresh
`init` BEFORE any other client touches the port.

If you also run LF-assist against the same Editor, ONE of the two tools
mints the session after Editor restart — whichever runs `init` first. The
other reads the cached ID. To share, point both at the same cache file via
the UE5_MCP_SESSION_FILE environment variable.

Protocol quirks that must be respected:
  - Send protocolVersion "2024-11-05" exactly on initialize.
  - Do NOT send an Accept header — its presence suppresses the session header.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MCP_URL = "http://localhost:13580/mcp"
TIMEOUT = 30

DEFAULT_CACHE = Path(__file__).parent / ".cache" / "ue5-bridge-session.json"
SESSION_EXPIRED_MARKERS = ("session required", "session not found", "invalid session")

INIT_BODY = {
    "jsonrpc": "2.0",
    "id": "init",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "ue5-materials", "version": "3.0"},
    },
}


class BridgeDead(Exception):
    """MCPBridge is not reachable — Editor not running or port 13580 closed."""


class SessionExpired(Exception):
    """Server says the session is no longer valid."""


class BridgeDegraded(Exception):
    """Server is reachable but will not mint a session — Editor needs a restart."""


class SessionLost(Exception):
    """Cached session is stale and no new one can be minted without a restart."""


def _cache_path() -> Path:
    override = os.environ.get("UE5_MCP_SESSION_FILE")
    return Path(override) if override else DEFAULT_CACHE


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict:
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _post(body: dict, session_id: str | None):
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(MCP_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return raw, resp.headers.get("Mcp-Session-Id")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        if any(m in err_body.lower() for m in SESSION_EXPIRED_MARKERS):
            raise SessionExpired(err_body) from e
        raise RuntimeError(f"HTTP {e.code} from MCPBridge: {err_body[:400]}") from e
    except (ConnectionRefusedError, urllib.error.URLError) as e:
        raise BridgeDead(str(e)) from e


def initialize() -> str:
    raw, session_id = _post(INIT_BODY, session_id=None)
    if not session_id:
        try:
            session_id = (json.loads(raw).get("result") or {}).get("sessionId")
        except json.JSONDecodeError:
            session_id = None
    if not session_id:
        raise BridgeDegraded(
            "initialize did not return a session id — Editor may need a restart"
        )
    state = load_state()
    state.update(mcp_session_id=session_id, mcp_verified_at=_utcnow_iso())
    save_state(state)
    return session_id


def _parse_tool_result(raw: str):
    envelope = json.loads(raw)
    if "error" in envelope:
        msg = envelope["error"].get("message", "")
        if any(m in msg.lower() for m in SESSION_EXPIRED_MARKERS):
            raise SessionExpired(msg)
        raise RuntimeError(f"MCP error: {msg}")
    result = envelope.get("result") or {}
    content = result.get("content") or []
    text = content[0].get("text", "") if content else ""
    if result.get("isError"):
        if any(m in text.lower() for m in SESSION_EXPIRED_MARKERS):
            raise SessionExpired(text)
        raise RuntimeError(f"Tool error: {text}")
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def call_tool(name: str, arguments: dict, session_id: str):
    import time
    body = {
        "jsonrpc": "2.0",
        "id": f"call-{name}-{int(time.time() * 1000)}",
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    raw, _ = _post(body, session_id=session_id)
    return _parse_tool_result(raw)


def ensure_session(force_new: bool = False) -> str:
    state = load_state()
    if not force_new and state.get("mcp_session_id"):
        return state["mcp_session_id"]
    return initialize()


def call(name: str, arguments: dict):
    """Call a tool with automatic session refresh on expiry."""
    session_id = ensure_session()
    try:
        return call_tool(name, arguments, session_id)
    except SessionExpired:
        try:
            session_id = initialize()
        except BridgeDegraded as e:
            raise SessionLost(str(e)) from e
        return call_tool(name, arguments, session_id)


def is_alive() -> bool:
    """Probe the bridge. Returns True if we can call a tool successfully."""
    try:
        call("get_editor_state", {})
        return True
    except (BridgeDead, BridgeDegraded, SessionLost):
        return False
    except Exception:
        return False


# ---------- CLI ----------

def _cmd_init(_args) -> int:
    try:
        session_id = initialize()
    except BridgeDead as e:
        print(f"MCPBridge: dead ({e})", file=sys.stderr)
        return 2
    except BridgeDegraded as e:
        print(f"MCPBridge: degraded ({e}) — restart the Editor", file=sys.stderr)
        return 3
    print(session_id)
    return 0


def _cmd_status(_args) -> int:
    try:
        info = call("get_editor_state", {})
    except BridgeDead:
        print("MCPBridge: dead")
        return 2
    except SessionLost as e:
        print(f"MCPBridge: session-lost ({e}). Restart Editor and run `init` first.")
        return 4
    except BridgeDegraded as e:
        print(f"MCPBridge: degraded ({e})")
        return 3
    except Exception as e:
        print(f"MCPBridge: error ({e})")
        return 1
    mp = info.get("map_name") or info.get("current_level") or "?"
    mode = info.get("editor_mode") or info.get("mode") or "?"
    sess = (load_state().get("mcp_session_id") or "")[:8]
    print(f"MCPBridge: alive (map={mp}, mode={mode}, session={sess}...)")
    return 0


def _cmd_call(args) -> int:
    try:
        arguments = json.loads(args.json_args) if args.json_args else {}
    except json.JSONDecodeError as e:
        print(f"invalid JSON args: {e}", file=sys.stderr)
        return 1
    try:
        result = call(args.tool_name, arguments)
    except Exception as e:
        print(f"call failed: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="mcp_bridge_client.py",
        description="MCPBridge helper — session handshake and tool calls for ue5-materials.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Mint a new MCP session and cache it")
    sub.add_parser("status", help="Check whether MCPBridge is reachable")
    c = sub.add_parser("call", help="Call an MCP tool by name")
    c.add_argument("tool_name")
    c.add_argument("json_args", nargs="?", default="{}")
    args = p.parse_args()
    return {"init": _cmd_init, "status": _cmd_status, "call": _cmd_call}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
