import { chmodSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

export function configPath(env = process.env) {
  if (env.AGENT_RELAY_CONFIG) return env.AGENT_RELAY_CONFIG;
  const root = env.LOCALAPPDATA || env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return join(root, "agent-relay", "config.json");
}

export function loadConfig({ env = process.env, optional = true } = {}) {
  const path = configPath(env);
  try {
    const config = JSON.parse(readFileSync(path, "utf8"));
    return { ...config, path };
  } catch (error) {
    if (optional && error?.code === "ENOENT") return { path };
    throw error;
  }
}

export function saveConfig(config, { env = process.env } = {}) {
  const path = configPath(env);
  mkdirSync(dirname(path), { recursive: true });
  const persisted = { ...config };
  delete persisted.path;
  writeFileSync(path, `${JSON.stringify(persisted, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  try { chmodSync(path, 0o600); } catch { /* Windows uses user ACLs. */ }
  return path;
}

export function connectionSettings(options = {}, env = process.env) {
  const config = loadConfig({ env });
  return {
    url: options.url || env.AGENT_RELAY_URL || config.url,
    token: options["broker-token"] || env.AGENT_RELAY_TOKEN || config.token,
    config,
  };
}
