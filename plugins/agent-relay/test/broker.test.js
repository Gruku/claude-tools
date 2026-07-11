import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { after, before, test } from "node:test";

import { AgentRelay } from "../src/relay.js";
import { createBrokerServer } from "../src/broker.js";

const root = mkdtempSync(join(process.cwd(), ".agent-relay-broker-test-"));
const relay = new AgentRelay({ databasePath: join(root, "relay.sqlite") });
const server = createBrokerServer({ relay, token: "test-broker-secret" });
let url;

before(async () => {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  url = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
  relay.close();
  rmSync(root, { recursive: true, force: true });
});

async function command(command, options = {}, credentials) {
  return fetch(`${url}/v1/command`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: "Bearer test-broker-secret" },
    body: JSON.stringify({ command, options, credentials }),
  });
}

test("broker rejects missing authentication", async () => {
  const response = await fetch(`${url}/v1/command`, { method: "POST", body: "{}" });
  assert.equal(response.status, 401);
});

test("pairing code can be exchanged only once", async () => {
  const pairedRelay = new AgentRelay();
  const pairedServer = createBrokerServer({
    relay: pairedRelay,
    token: "paired-broker-secret",
    pairingCode: "123456",
    pairingExpiresAt: Date.now() + 60_000,
  });
  await new Promise((resolve) => pairedServer.listen(0, "127.0.0.1", resolve));
  const pairUrl = `http://127.0.0.1:${pairedServer.address().port}/v1/pair`;
  const first = await fetch(pairUrl, { method: "POST", body: JSON.stringify({ code: "123456" }) });
  const second = await fetch(pairUrl, { method: "POST", body: JSON.stringify({ code: "123456" }) });
  assert.equal((await first.json()).token, "paired-broker-secret");
  assert.equal(second.status, 401);
  await new Promise((resolve) => pairedServer.close(resolve));
  pairedRelay.close();
});

test("two remote clients see the same authoritative relay", async () => {
  const codexResponse = await command("join", { label: "codex-wsl", host: "codex", rooms: ["general"] });
  const claudeResponse = await command("join", { label: "claude-windows", host: "claude", rooms: ["general"] });
  const codex = (await codexResponse.json()).result;
  const claude = (await claudeResponse.json()).result;

  const who = await command("who", {}, codex.credentials);
  const peers = (await who.json()).result;
  assert.deepEqual(peers.map((peer) => peer.label), ["codex-wsl", "claude-windows"]);

  await command("send", { toSessionId: claude.session.id, body: "Cross the OS boundary." }, codex.credentials);
  const inbox = await command("inbox", {}, claude.credentials);
  assert.equal((await inbox.json()).result[0].body, "Cross the OS boundary.");
});
