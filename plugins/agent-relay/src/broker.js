import { timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";

import { RelayAuthError, RelayError } from "./relay.js";

function authorized(request, token) {
  const supplied = request.headers.authorization?.replace(/^Bearer\s+/i, "") ?? "";
  const expected = Buffer.from(token);
  const actual = Buffer.from(supplied);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

function invoke(relay, command, credentials, options = {}) {
  switch (command) {
    case "join": return relay.join(options);
    case "who": return relay.who(credentials);
    case "send": return relay.send(credentials, options);
    case "request": return relay.request(credentials, options);
    case "reply": return relay.reply(credentials, options);
    case "inbox": return relay.inbox(credentials, options);
    case "leave": return relay.leave(credentials);
    default: throw new RelayError(`unknown command: ${command}`);
  }
}

function respond(response, status, body) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(`${JSON.stringify(body)}\n`);
}

export function createBrokerServer({ relay, token, pairingCode, pairingExpiresAt = 0 }) {
  if (typeof token !== "string" || token.length < 16) throw new Error("broker token must contain at least 16 characters");
  let activePairingCode = pairingCode;
  return createServer(async (request, response) => {
    if (request.method === "GET" && request.url === "/v1/health") {
      respond(response, 200, { ok: true, service: "agent-relay" });
      return;
    }
    if (request.method === "POST" && request.url === "/v1/pair") {
      try {
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        const { code } = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        if (!activePairingCode || Date.now() >= pairingExpiresAt || code !== activePairingCode) {
          respond(response, 401, { error: "pairing code is invalid or expired" });
          return;
        }
        activePairingCode = undefined;
        respond(response, 200, { token });
      } catch (error) {
        respond(response, 400, { error: error.message });
      }
      return;
    }
    if (request.method === "GET" && request.url === "/v1/auth-check") {
      if (!authorized(request, token)) {
        respond(response, 401, { error: "broker authentication failed" });
        return;
      }
      respond(response, 200, { ok: true });
      return;
    }
    if (request.method !== "POST" || request.url !== "/v1/command") {
      respond(response, 404, { error: "not found" });
      return;
    }
    if (!authorized(request, token)) {
      respond(response, 401, { error: "broker authentication failed" });
      return;
    }
    try {
      const chunks = [];
      let size = 0;
      for await (const chunk of request) {
        size += chunk.length;
        if (size > 1_000_000) throw new RelayError("request body is too large");
        chunks.push(chunk);
      }
      const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      respond(response, 200, { result: invoke(relay, payload.command, payload.credentials, payload.options) });
    } catch (error) {
      const status = error instanceof RelayAuthError ? 401 : error instanceof RelayError || error instanceof SyntaxError ? 400 : 500;
      respond(response, status, { error: error.message });
    }
  });
}
