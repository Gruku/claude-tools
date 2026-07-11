import assert from "node:assert/strict";
import { afterEach, describe, test } from "node:test";

import { AgentRelay, RelayAuthError, RelayValidationError } from "../src/relay.js";

const relays = [];

function makeRelay(options = {}) {
  const relay = new AgentRelay({ databasePath: ":memory:", ...options });
  relays.push(relay);
  return relay;
}

afterEach(() => {
  while (relays.length) relays.pop().close();
});

describe("explicit session gating", () => {
  test("joined sessions can discover one another but invalid credentials cannot", () => {
    const relay = makeRelay();
    const codex = relay.join({ label: "codex-plan", host: "codex", rooms: ["review"] });
    const claude = relay.join({ label: "claude-critic", host: "claude", rooms: ["review"] });

    assert.deepEqual(
      relay.who(codex.credentials).map(({ label, host }) => ({ label, host })),
      [
        { label: "codex-plan", host: "codex" },
        { label: "claude-critic", host: "claude" },
      ],
    );
    assert.throws(
      () => relay.who({ sessionId: codex.session.id, token: "wrong" }),
      RelayAuthError,
    );
  });

  test("expired and explicitly left sessions lose access", () => {
    let now = 1_000;
    const relay = makeRelay({ now: () => now, defaultTtlMs: 100 });
    const expired = relay.join({ label: "short-lived", host: "codex" });
    now = 1_101;
    assert.throws(() => relay.who(expired.credentials), RelayAuthError);

    const active = relay.join({ label: "leaving", host: "claude" });
    relay.leave(active.credentials);
    assert.throws(() => relay.who(active.credentials), RelayAuthError);
  });
});

describe("direct and room communication", () => {
  test("delivers a DM only to its target and does not echo it to the sender", () => {
    const relay = makeRelay();
    const codex = relay.join({ label: "codex", host: "codex" });
    const claude = relay.join({ label: "claude", host: "claude" });
    const observer = relay.join({ label: "observer", host: "codex" });

    relay.send(codex.credentials, {
      toSessionId: claude.session.id,
      body: "Please challenge assumption three.",
    });

    assert.equal(relay.inbox(claude.credentials).length, 1);
    assert.equal(relay.inbox(codex.credentials).length, 0);
    assert.equal(relay.inbox(observer.credentials).length, 0);
  });

  test("delivers room messages to joined peers only", () => {
    const relay = makeRelay();
    const sender = relay.join({ label: "sender", host: "codex", rooms: ["architecture"] });
    const member = relay.join({ label: "member", host: "claude", rooms: ["architecture"] });
    const outsider = relay.join({ label: "outsider", host: "codex", rooms: ["other"] });

    relay.send(sender.credentials, { toRoom: "architecture", body: "Thoughts on leases?" });

    assert.equal(relay.inbox(member.credentials).length, 1);
    assert.equal(relay.inbox(sender.credentials).length, 0);
    assert.equal(relay.inbox(outsider.credentials).length, 0);
  });

  test("rejects ambiguous targets and sends to active sessions only", () => {
    const relay = makeRelay();
    const sender = relay.join({ label: "sender", host: "codex", rooms: ["review"] });
    const target = relay.join({ label: "target", host: "claude", rooms: ["review"] });
    relay.leave(target.credentials);

    assert.throws(
      () => relay.send(sender.credentials, { toSessionId: target.session.id, toRoom: "review", body: "x" }),
      RelayValidationError,
    );
    assert.throws(
      () => relay.send(sender.credentials, { toSessionId: target.session.id, body: "x" }),
      RelayValidationError,
    );
  });
});

describe("review request lifecycle", () => {
  test("correlates a reply with the original request", () => {
    const relay = makeRelay();
    const codex = relay.join({ label: "codex", host: "codex" });
    const claude = relay.join({ label: "claude", host: "claude" });

    const request = relay.request(codex.credentials, {
      toSessionId: claude.session.id,
      body: "Adversarially review this plan.",
    });
    const received = relay.inbox(claude.credentials)[0];
    const reply = relay.reply(claude.credentials, {
      requestId: received.id,
      body: "The rollback path is underspecified.",
    });

    assert.equal(received.kind, "request");
    assert.equal(reply.correlationId, request.correlationId);
    assert.equal(reply.inReplyTo, request.id);
    assert.equal(relay.inbox(codex.credentials)[0].body, "The rollback path is underspecified.");
  });

  test("only the request target can reply", () => {
    const relay = makeRelay();
    const codex = relay.join({ label: "codex", host: "codex" });
    const claude = relay.join({ label: "claude", host: "claude" });
    const observer = relay.join({ label: "observer", host: "claude" });
    const request = relay.request(codex.credentials, {
      toSessionId: claude.session.id,
      body: "Review this.",
    });

    assert.throws(
      () => relay.reply(observer.credentials, { requestId: request.id, body: "Intercepted" }),
      RelayValidationError,
    );
  });
});
