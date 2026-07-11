import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const pluginRoot = process.cwd();
const repositoryRoot = join(pluginRoot, "..", "..");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

test("dual-host manifests stay version-aligned", () => {
  const codex = readJson(join(pluginRoot, ".codex-plugin", "plugin.json"));
  const claude = readJson(join(pluginRoot, ".claude-plugin", "plugin.json"));
  const packageJson = readJson(join(pluginRoot, "package.json"));
  const claudeMarketplace = readJson(join(repositoryRoot, ".claude-plugin", "marketplace.json"));

  assert.equal(codex.version, "0.1.0");
  assert.equal(claude.version, codex.version);
  assert.equal(packageJson.version, codex.version);
  assert.equal(
    claudeMarketplace.plugins.find(({ name }) => name === "agent-relay")?.version,
    codex.version,
  );
});

test("each host receives its supported MCP configuration shape", () => {
  const codex = readJson(join(pluginRoot, ".codex-plugin", "plugin.json"));
  const claudeMcp = readJson(join(pluginRoot, ".mcp.json"));
  const codexServer = codex.mcpServers["agent-relay"];
  const claudeServer = claudeMcp.mcpServers["agent-relay"];

  assert.equal(codexServer.cwd, ".");
  assert.equal(codexServer.startup_timeout_sec, 120);
  assert.match(codexServer.args.join(" "), /fastmcp==3\.4\.4/);
  assert.match(codexServer.args.join(" "), /mcp_server\.py/);
  assert.match(claudeServer.args.join(" "), /fastmcp==3\.4\.4/);
  assert.match(claudeServer.args.join(" "), /\$\{CLAUDE_PLUGIN_ROOT\}/);
});

test("the Codex repository marketplace exposes Agent Relay", () => {
  const marketplace = readJson(join(repositoryRoot, ".agents", "plugins", "marketplace.json"));
  const entry = marketplace.plugins.find(({ name }) => name === "agent-relay");

  assert.equal(marketplace.name, "gruku-tools");
  assert.equal(entry.source.path, "./plugins/agent-relay");
  assert.equal(entry.policy.installation, "AVAILABLE");
  assert.equal(entry.policy.authentication, "ON_INSTALL");
});
