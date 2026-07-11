#!/usr/bin/env node

import { chmodSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { homedir } from "node:os";

import { AgentRelay, RelayError } from "../src/relay.js";

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const options = {};
  for (let index = 0; index < rest.length; index += 1) {
    const item = rest[index];
    if (!item.startsWith("--")) throw new Error(`unexpected argument: ${item}`);
    const key = item.slice(2);
    const value = rest[index + 1];
    if (value === undefined) throw new Error(`missing value for --${key}`);
    options[key] = value;
    index += 1;
  }
  return { command, options };
}

function help() {
  return `Agent Relay CLI

Usage:
  agent-relay join --profile PATH --label NAME --host codex|claude [--rooms review,team]
  agent-relay who --profile PATH
  agent-relay send --profile PATH (--to SESSION_ID | --room ROOM) --body TEXT
  agent-relay request --profile PATH --to SESSION_ID --body TEXT
  agent-relay reply --profile PATH --request MESSAGE_ID --body TEXT
  agent-relay inbox --profile PATH [--after SEQUENCE] [--limit COUNT]
  agent-relay leave --profile PATH

Options:
  --database PATH   Override the shared SQLite database.
  --profile PATH    Explicit per-chat credential file. Also accepted through AGENT_RELAY_PROFILE.
`;
}

function relayDatabasePath(options) {
  if (options.database) return options.database;
  if (process.env.AGENT_RELAY_DATABASE) return process.env.AGENT_RELAY_DATABASE;
  const stateRoot = process.env.LOCALAPPDATA || process.env.XDG_STATE_HOME || join(homedir(), ".local", "state");
  return join(stateRoot, "agent-relay", "relay.sqlite");
}

function profilePath(options) {
  const path = options.profile || process.env.AGENT_RELAY_PROFILE;
  if (!path) throw new Error("--profile is required so joining remains explicit per CLI chat");
  return path;
}

function ensureParent(path) {
  mkdirSync(dirname(path), { recursive: true });
}

function loadCredentials(options) {
  const path = profilePath(options);
  const profile = JSON.parse(readFileSync(path, "utf8"));
  if (!profile.sessionId || !profile.token) throw new Error(`invalid relay profile: ${path}`);
  return profile;
}

function saveCredentials(options, credentials) {
  const path = profilePath(options);
  ensureParent(path);
  writeFileSync(path, `${JSON.stringify(credentials, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  try { chmodSync(path, 0o600); } catch { /* Windows ACLs are managed separately. */ }
}

function target(options) {
  return { toSessionId: options.to, toRoom: options.room };
}

function main() {
  const { command, options } = parseArgs(process.argv.slice(2));
  if (!command || command === "help" || command === "--help") {
    process.stdout.write(help());
    return;
  }

  const databasePath = relayDatabasePath(options);
  ensureParent(databasePath);
  const relay = new AgentRelay({ databasePath });
  try {
    let result;
    switch (command) {
      case "join": {
        result = relay.join({
          label: options.label,
          host: options.host,
          rooms: options.rooms ? options.rooms.split(",").map((room) => room.trim()).filter(Boolean) : [],
          ttlMs: options.ttl ? Number(options.ttl) : undefined,
        });
        saveCredentials(options, result.credentials);
        result = { session: result.session, profile: profilePath(options) };
        break;
      }
      case "who":
        result = relay.who(loadCredentials(options));
        break;
      case "send":
        result = relay.send(loadCredentials(options), { ...target(options), body: options.body });
        break;
      case "request":
        result = relay.request(loadCredentials(options), { toSessionId: options.to, body: options.body });
        break;
      case "reply":
        result = relay.reply(loadCredentials(options), { requestId: options.request, body: options.body });
        break;
      case "inbox":
        result = relay.inbox(loadCredentials(options), {
          afterSequence: options.after ? Number(options.after) : 0,
          limit: options.limit ? Number(options.limit) : 100,
        });
        break;
      case "leave":
        result = relay.leave(loadCredentials(options));
        break;
      default:
        throw new Error(`unknown command: ${command}`);
    }
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } finally {
    relay.close();
  }
}

try {
  main();
} catch (error) {
  const expected = error instanceof RelayError || error instanceof SyntaxError || error?.code === "ENOENT";
  process.stderr.write(`${expected ? "Agent Relay" : "Agent Relay internal error"}: ${error.message}\n`);
  process.exitCode = 1;
}
