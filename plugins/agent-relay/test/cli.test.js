import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { after, test } from "node:test";

const tempRoot = mkdtempSync(join(process.cwd(), ".agent-relay-test-"));
const database = join(tempRoot, "relay.sqlite");
const codexProfile = join(tempRoot, "codex.json");
const claudeProfile = join(tempRoot, "claude.json");
const cli = join(process.cwd(), "scripts", "agent-relay.js");

after(() => rmSync(tempRoot, { recursive: true, force: true }));

function run(...args) {
  const result = spawnSync(process.execPath, [cli, ...args, "--database", database], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("two standalone CLI profiles exchange a review request", () => {
  const codex = run(
    "join", "--profile", codexProfile, "--label", "codex-plan", "--host", "codex", "--rooms", "review",
  );
  const claude = run(
    "join", "--profile", claudeProfile, "--label", "claude-critic", "--host", "claude", "--rooms", "review",
  );

  run(
    "request", "--profile", codexProfile, "--to", claude.session.id,
    "--body", "Adversarially review the plan.",
  );
  const inbox = run("inbox", "--profile", claudeProfile);

  assert.equal(codex.session.host, "codex");
  assert.equal(inbox.length, 1);
  assert.equal(inbox[0].kind, "request");
  assert.equal(inbox[0].body, "Adversarially review the plan.");
});
