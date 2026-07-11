#!/usr/bin/env node

import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { parseArgs } from "node:util";

import { createBrokerServer } from "../src/broker.js";
import { AgentRelay } from "../src/relay.js";

const { values } = parseArgs({ options: {
  host: { type: "string", default: "127.0.0.1" },
  port: { type: "string", default: "43127" },
  database: { type: "string" },
  token: { type: "string" },
} });
const database = values.database || process.env.AGENT_RELAY_DATABASE;
const token = values.token || process.env.AGENT_RELAY_TOKEN;
if (!database) throw new Error("--database or AGENT_RELAY_DATABASE is required");
if (!token) throw new Error("--token or AGENT_RELAY_TOKEN is required");
mkdirSync(dirname(database), { recursive: true });
const relay = new AgentRelay({ databasePath: database });
const server = createBrokerServer({ relay, token });
server.listen(Number(values.port), values.host, () => {
  process.stderr.write(`Agent Relay broker listening on http://${values.host}:${values.port}\n`);
});
function shutdown() { server.close(() => { relay.close(); process.exit(0); }); }
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
