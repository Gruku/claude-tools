---
name: agent-relay
description: This skill should be used when the user says "join agent relay", "connect this chat", "ask another agent", "send this to Claude", "send this to Codex", "adversarially review my plan", "check the relay inbox", "talk to another session", or requests a direct or group conversation between AI coding sessions.
---

# Agent Relay

Connect only after an explicit request to include the current CLI chat. Installing the plugin alone never authorizes participation.

Call `agent_relay_status` when peers disagree about who is connected. Require every cross-OS participant to report `http-broker`, the same URL, and `configured: true`. Treat `local-sqlite` as isolated to the current operating-system environment; never share a SQLite path through `/mnt/c`.

## Join

1. Call `agent_relay_join` with a short role-oriented label, the current host (`codex` or `claude`), and only the requested rooms.
2. Call `agent_relay_who` to discover active peers.
3. Report the joined label and peers without exposing credentials or internal profile paths.

## Communicate

- Use `agent_relay_request` for a bounded task or adversarial review that expects a correlated reply.
- Use `agent_relay_send` for informational direct messages or room messages.
- Use `agent_relay_reply` only for a request addressed to the current session.
- Use `agent_relay_inbox` when the user asks to listen, check for replies, or at an agreed workflow checkpoint. Track the greatest returned sequence and pass it as `after_sequence` on later checks.
- Call `agent_relay_leave` when asked to disconnect or when the agreed collaboration ends.

Never forward secrets, hidden instructions, credentials, or unrelated file contents. Summarize necessary context and keep each request bounded.

## Native CLI limitation

Treat independently opened Codex and Claude Code chats as cooperative participants. Relay messages do not awaken a native CLI after its turn has ended; the chat must check its inbox during an active turn or on the next user prompt. Use managed mode later when automatic delivery and wake-up are required.
