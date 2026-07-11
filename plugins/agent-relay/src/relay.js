import { createHash, randomBytes, randomUUID } from "node:crypto";
import { DatabaseSync } from "node:sqlite";

export class RelayError extends Error {}
export class RelayAuthError extends RelayError {}
export class RelayValidationError extends RelayError {}

const HOSTS = new Set(["codex", "claude", "other"]);
const KINDS = new Set(["message", "request", "reply"]);

function tokenHash(token) {
  return createHash("sha256").update(token).digest("hex");
}

function requireText(value, field, maxLength = 65_536) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new RelayValidationError(`${field} must be a non-empty string`);
  }
  if (value.length > maxLength) {
    throw new RelayValidationError(`${field} exceeds ${maxLength} characters`);
  }
  return value.trim();
}

function mapMessage(row) {
  return {
    id: row.message_id,
    sequence: row.sequence,
    kind: row.kind,
    fromSessionId: row.sender_session_id,
    toSessionId: row.target_session_id ?? undefined,
    toRoom: row.target_room ?? undefined,
    body: row.body,
    correlationId: row.correlation_id ?? undefined,
    inReplyTo: row.in_reply_to ?? undefined,
    createdAt: row.created_at,
  };
}

export class AgentRelay {
  constructor({ databasePath = ":memory:", now = Date.now, defaultTtlMs = 15 * 60_000 } = {}) {
    if (!Number.isSafeInteger(defaultTtlMs) || defaultTtlMs <= 0) {
      throw new RelayValidationError("defaultTtlMs must be a positive integer");
    }
    this.db = new DatabaseSync(databasePath);
    this.now = now;
    this.defaultTtlMs = defaultTtlMs;
    this.db.exec("PRAGMA foreign_keys = ON");
    this.db.exec("PRAGMA busy_timeout = 5000");
    if (databasePath !== ":memory:") this.db.exec("PRAGMA journal_mode = WAL");
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL UNIQUE,
        token_hash TEXT NOT NULL,
        label TEXT NOT NULL,
        host TEXT NOT NULL,
        status TEXT NOT NULL,
        ttl_ms INTEGER NOT NULL,
        joined_at INTEGER NOT NULL,
        last_seen_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS memberships (
        session_id TEXT NOT NULL,
        room TEXT NOT NULL,
        joined_at INTEGER NOT NULL,
        PRIMARY KEY (session_id, room),
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
      );
      CREATE TABLE IF NOT EXISTS messages (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL,
        sender_session_id TEXT NOT NULL,
        target_session_id TEXT,
        target_room TEXT,
        body TEXT NOT NULL,
        correlation_id TEXT,
        in_reply_to TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (sender_session_id) REFERENCES sessions(session_id),
        FOREIGN KEY (target_session_id) REFERENCES sessions(session_id)
      );
      CREATE INDEX IF NOT EXISTS idx_messages_direct ON messages(target_session_id, sequence);
      CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(target_room, sequence);
    `);
  }

  close() {
    this.db.close();
  }

  join({ label, host, rooms = [], ttlMs = this.defaultTtlMs }) {
    label = requireText(label, "label", 80);
    if (!HOSTS.has(host)) {
      throw new RelayValidationError(`host must be one of: ${[...HOSTS].join(", ")}`);
    }
    if (!Array.isArray(rooms) || !Number.isSafeInteger(ttlMs) || ttlMs <= 0) {
      throw new RelayValidationError("rooms must be an array and ttlMs must be a positive integer");
    }

    const normalizedRooms = [...new Set(rooms.map((room) => requireText(room, "room", 80)))];
    const sessionId = randomUUID();
    const token = randomBytes(32).toString("base64url");
    const joinedAt = this.now();

    this.db.exec("BEGIN IMMEDIATE");
    try {
      this.db.prepare(`
        INSERT INTO sessions (
          session_id, token_hash, label, host, status, ttl_ms, joined_at, last_seen_at, expires_at
        ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?)
      `).run(sessionId, tokenHash(token), label, host, ttlMs, joinedAt, joinedAt, joinedAt + ttlMs);
      const addMembership = this.db.prepare(
        "INSERT INTO memberships (session_id, room, joined_at) VALUES (?, ?, ?)",
      );
      for (const room of normalizedRooms) addMembership.run(sessionId, room, joinedAt);
      this.db.exec("COMMIT");
    } catch (error) {
      this.db.exec("ROLLBACK");
      throw error;
    }

    return {
      session: { id: sessionId, label, host, rooms: normalizedRooms, joinedAt, expiresAt: joinedAt + ttlMs },
      credentials: { sessionId, token },
    };
  }

  leave(credentials) {
    const session = this.#authenticate(credentials, { touch: false });
    this.db.prepare("UPDATE sessions SET status = 'left' WHERE session_id = ?").run(session.session_id);
    return { left: true, sessionId: session.session_id };
  }

  who(credentials) {
    this.#authenticate(credentials);
    const now = this.now();
    return this.db.prepare(`
      SELECT session_id, label, host, joined_at, last_seen_at, expires_at
      FROM sessions
      WHERE status = 'active' AND expires_at > ?
      ORDER BY sequence
    `).all(now).map((row) => ({
      id: row.session_id,
      label: row.label,
      host: row.host,
      joinedAt: row.joined_at,
      lastSeenAt: row.last_seen_at,
      expiresAt: row.expires_at,
    }));
  }

  send(credentials, message) {
    return this.#createMessage(credentials, { ...message, kind: "message" });
  }

  request(credentials, message) {
    if (!message?.toSessionId || message.toRoom) {
      throw new RelayValidationError("requests currently require exactly one direct session target");
    }
    return this.#createMessage(credentials, {
      ...message,
      kind: "request",
      correlationId: randomUUID(),
    });
  }

  reply(credentials, { requestId, body }) {
    const sender = this.#authenticate(credentials);
    requestId = requireText(requestId, "requestId", 80);
    const request = this.db.prepare(
      "SELECT * FROM messages WHERE message_id = ? AND kind = 'request'",
    ).get(requestId);
    if (!request || request.target_session_id !== sender.session_id) {
      throw new RelayValidationError("request does not exist or is not addressed to this session");
    }
    return this.#insertMessage({
      kind: "reply",
      senderSessionId: sender.session_id,
      toSessionId: request.sender_session_id,
      body,
      correlationId: request.correlation_id,
      inReplyTo: request.message_id,
    });
  }

  inbox(credentials, { afterSequence = 0, limit = 100 } = {}) {
    const session = this.#authenticate(credentials);
    if (!Number.isSafeInteger(afterSequence) || afterSequence < 0) {
      throw new RelayValidationError("afterSequence must be a non-negative integer");
    }
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 500) {
      throw new RelayValidationError("limit must be between 1 and 500");
    }
    return this.db.prepare(`
      SELECT m.*
      FROM messages m
      WHERE m.sequence > ?
        AND m.sender_session_id <> ?
        AND (
          m.target_session_id = ?
          OR EXISTS (
            SELECT 1 FROM memberships membership
            WHERE membership.session_id = ?
              AND membership.room = m.target_room
              AND m.created_at >= membership.joined_at
          )
        )
      ORDER BY m.sequence
      LIMIT ?
    `).all(afterSequence, session.session_id, session.session_id, session.session_id, limit)
      .map(mapMessage);
  }

  #createMessage(credentials, { kind, toSessionId, toRoom, body, correlationId }) {
    const sender = this.#authenticate(credentials);
    if (!KINDS.has(kind)) throw new RelayValidationError("unsupported message kind");
    if (Boolean(toSessionId) === Boolean(toRoom)) {
      throw new RelayValidationError("provide exactly one of toSessionId or toRoom");
    }

    if (toSessionId) {
      toSessionId = requireText(toSessionId, "toSessionId", 80);
      const target = this.db.prepare(`
        SELECT 1 FROM sessions
        WHERE session_id = ? AND status = 'active' AND expires_at > ?
      `).get(toSessionId, this.now());
      if (!target) throw new RelayValidationError("target session is not active");
    } else {
      toRoom = requireText(toRoom, "toRoom", 80);
      const member = this.db.prepare(
        "SELECT 1 FROM memberships WHERE session_id = ? AND room = ?",
      ).get(sender.session_id, toRoom);
      if (!member) throw new RelayValidationError("sender has not joined the target room");
    }

    return this.#insertMessage({
      kind,
      senderSessionId: sender.session_id,
      toSessionId,
      toRoom,
      body,
      correlationId,
    });
  }

  #insertMessage({ kind, senderSessionId, toSessionId, toRoom, body, correlationId, inReplyTo }) {
    body = requireText(body, "body");
    const messageId = randomUUID();
    const createdAt = this.now();
    const result = this.db.prepare(`
      INSERT INTO messages (
        message_id, kind, sender_session_id, target_session_id, target_room,
        body, correlation_id, in_reply_to, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      messageId,
      kind,
      senderSessionId,
      toSessionId ?? null,
      toRoom ?? null,
      body,
      correlationId ?? null,
      inReplyTo ?? null,
      createdAt,
    );
    return mapMessage(this.db.prepare("SELECT * FROM messages WHERE sequence = ?").get(result.lastInsertRowid));
  }

  #authenticate(credentials, { touch = true } = {}) {
    if (!credentials || typeof credentials.sessionId !== "string" || typeof credentials.token !== "string") {
      throw new RelayAuthError("session credentials are required");
    }
    const now = this.now();
    const session = this.db.prepare("SELECT * FROM sessions WHERE session_id = ?").get(credentials.sessionId);
    if (
      !session
      || session.status !== "active"
      || session.expires_at <= now
      || session.token_hash !== tokenHash(credentials.token)
    ) {
      throw new RelayAuthError("session credentials are invalid or expired");
    }
    if (touch) {
      const expiresAt = now + session.ttl_ms;
      this.db.prepare(
        "UPDATE sessions SET last_seen_at = ?, expires_at = ? WHERE session_id = ?",
      ).run(now, expiresAt, session.session_id);
      session.last_seen_at = now;
      session.expires_at = expiresAt;
    }
    return session;
  }
}
