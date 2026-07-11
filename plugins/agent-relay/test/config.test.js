import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { after, test } from "node:test";

import { connectionSettings, loadConfig, saveConfig } from "../src/config.js";

const root = mkdtempSync(join(process.cwd(), ".agent-relay-config-test-"));
const env = { AGENT_RELAY_CONFIG: join(root, "config.json") };
after(() => rmSync(root, { recursive: true, force: true }));

test("persistent configuration supplies broker connection defaults", () => {
  saveConfig({ url: "http://broker:43127", token: "persistent-secret" }, { env });
  assert.equal(loadConfig({ env }).url, "http://broker:43127");
  assert.equal(connectionSettings({}, env).token, "persistent-secret");
  assert.equal(connectionSettings({ url: "http://override" }, env).url, "http://override");
});
