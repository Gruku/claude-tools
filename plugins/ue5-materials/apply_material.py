"""apply_material.py — YAML → UE5 material.

Two execution modes:
  - live:      drive the Material Editor via MCPBridge (create_material +
               add_material_expressions + connect_material_pins).
  - clipboard: emit T3D text for Ctrl+V paste into the Material Editor.
  - auto:     probe MCPBridge; live if reachable, else clipboard.

Every run is archived to .ue5-materials-history/<timestamp>.yaml so you
can replay or diff what you sent.

YAML schema (same as the clipboard generator's input):

    material_path: /Game/Materials/M_Example     # optional — else uses `material` name
    material: M_Example                          # short name
    shading_model: lit                            # optional (live mode only)
    blend_mode: opaque                            # optional (live mode only)
    two_sided: false                              # optional (live mode only)
    position_start: [0, 0]                        # optional
    spacing_x: 256                                # optional
    spacing_y: 96                                 # optional

    nodes:
      - name: MyConst
        type: Constant
        value: 0.5
      - name: MyColor
        type: Constant3Vector
        value: [1.0, 0.5, 0.2]

    connections:
      - MyConst -> MyColor.0          # pin index on target expression
      - MyColor -> BaseColor           # material root input (case-insensitive)

Limitations of live mode:
  - Types outside MCPBridge's hardcoded fast paths (Constant, Constant3Vector,
    ScalarParameter, VectorParameter, TextureSample, Add, Multiply, Lerp) use
    the dynamic UClass fallback — creation works, but properties like Custom
    HLSL code or MakeFloat4's MaterialFunction binding are NOT set. For those,
    use clipboard mode or post-process with mcp_bridge_client.py execute_python.
  - Target pins on an expression are identified by integer index (e.g. `.0`,
    `.1`). Named pin resolution via node_registry is a planned follow-up.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

import mcp_bridge_client as bridge

PLUGIN_DIR = Path(__file__).parent
HISTORY_DIR = PLUGIN_DIR / ".ue5-materials-history"

ROOT_INPUT_ALIASES = {
    "basecolor", "base_color",
    "metallic",
    "specular",
    "roughness",
    "emissivecolor", "emissive_color",
    "normal",
    "opacity",
    "opacitymask", "opacity_mask",
    "ambientocclusion", "ambient_occlusion",
}

CONNECTION_RE = re.compile(
    r"""^\s*
        (?P<src>[A-Za-z_][A-Za-z0-9_]*)          # source node
        (?:\.(?P<src_pin>[A-Za-z0-9_]+))?         # optional source pin
        \s*->\s*
        (?P<dst>[A-Za-z_][A-Za-z0-9_]*)           # target node OR root input
        (?:\.(?P<dst_pin>[A-Za-z0-9_]+))?         # optional target pin
        \s*$""",
    re.VERBOSE,
)


def archive_yaml(yaml_path: Path) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = HISTORY_DIR / f"{stamp}-{yaml_path.name}"
    shutil.copy2(yaml_path, dest)
    return dest


def split_material_path(spec: dict) -> tuple[str, str]:
    """Return (content_path_dir, material_name)."""
    name = spec.get("material") or spec.get("name")
    full = spec.get("material_path")
    if full:
        parts = full.rsplit("/", 1)
        if len(parts) == 2 and parts[1]:
            return parts[0], parts[1]
        return full, name or "M_Untitled"
    return "/Game/Materials", name or "M_Untitled"


def compute_positions(nodes: list[dict], spec: dict) -> list[tuple[float, float]]:
    """Use explicit positions if given, else lay out left-to-right."""
    pos_start = spec.get("position_start", [0, 0])
    sx = spec.get("spacing_x", 256)
    sy = spec.get("spacing_y", 96)
    out = []
    col = 0
    row = 0
    for n in nodes:
        pos = n.get("position")
        if pos and len(pos) == 2:
            out.append((float(pos[0]), float(pos[1])))
        else:
            out.append((pos_start[0] + col * sx, pos_start[1] + row * sy))
            row += 1
            if row > 6:
                row = 0
                col += 1
    return out


def translate_expression(node: dict, pos: tuple[float, float]) -> dict:
    """YAML node → add_material_expressions entry."""
    t = node["type"]
    entry = {"type": t, "pos_x": pos[0], "pos_y": pos[1]}
    if "name" in node:
        entry["name"] = node["name"]
    if "value" in node:
        entry["value"] = node["value"]
    if "default_value" in node:
        entry["default_value"] = node["default_value"]
    if "texture" in node:
        entry["texture"] = node["texture"]
    return entry


def resolve_pin(token: str | None) -> int | None:
    if token is None:
        return None
    if token.isdigit():
        return int(token)
    return None  # named pins are not yet supported in live mode


def is_root_input(token: str) -> bool:
    return token.replace("_", "").lower() in {s.replace("_", "") for s in ROOT_INPUT_ALIASES}


def parse_connection(conn: str) -> dict:
    m = CONNECTION_RE.match(conn)
    if not m:
        raise ValueError(f"unparseable connection: {conn!r}")
    return m.groupdict()


def apply_live(spec: dict, yaml_path: Path) -> int:
    if not bridge.is_alive():
        print("MCPBridge unreachable — run `python mcp_bridge_client.py init` "
              "after the Editor is up, or use --mode clipboard.", file=sys.stderr)
        return 2

    path_dir, mat_name = split_material_path(spec)
    nodes = spec.get("nodes", [])
    connections = spec.get("connections", [])
    if not nodes:
        print("no nodes in YAML — nothing to do", file=sys.stderr)
        return 1

    positions = compute_positions(nodes, spec)

    # 1. Create material
    create_args = {"name": mat_name, "path": path_dir}
    for k in ("shading_model", "blend_mode", "two_sided"):
        if k in spec:
            create_args[k] = spec[k]
    print(f"[live] create_material {mat_name} in {path_dir}")
    bridge.call("create_material", create_args)
    material_path = f"{path_dir.rstrip('/')}/{mat_name}"

    # 2. Batch-add expressions
    expressions_payload = [
        translate_expression(n, positions[i]) for i, n in enumerate(nodes)
    ]
    print(f"[live] add_material_expressions x{len(expressions_payload)}")
    result = bridge.call(
        "add_material_expressions",
        {"material_path": material_path, "expressions": expressions_payload},
    )
    created = result.get("created_expressions", []) if isinstance(result, dict) else []
    if len(created) != len(nodes):
        print(f"warning: asked for {len(nodes)} expressions, got {len(created)}",
              file=sys.stderr)
    name_to_index: dict[str, int] = {}
    for yaml_node, created_entry in zip(nodes, created):
        display_name = yaml_node.get("name") or created_entry.get("name")
        if display_name is not None:
            name_to_index[display_name] = int(created_entry["index"])

    # 3. Connections
    errors = 0
    for conn in connections:
        try:
            parts = parse_connection(conn)
        except ValueError as e:
            print(f"  skip: {e}", file=sys.stderr)
            errors += 1
            continue
        src_name = parts["src"]
        dst_name = parts["dst"]
        src_pin = resolve_pin(parts["src_pin"]) or 0
        dst_pin_token = parts["dst_pin"]

        if src_name not in name_to_index:
            print(f"  skip: unknown source node {src_name!r} in {conn!r}", file=sys.stderr)
            errors += 1
            continue
        args = {
            "material_path": material_path,
            "source_expression_index": name_to_index[src_name],
            "source_output_index": src_pin,
        }
        if dst_pin_token is None and is_root_input(dst_name):
            args["target_material_input"] = dst_name
        elif dst_name in name_to_index:
            args["target_expression_index"] = name_to_index[dst_name]
            dst_pin = resolve_pin(dst_pin_token)
            if dst_pin is None and dst_pin_token is not None:
                print(f"  skip: named target pin {dst_pin_token!r} not supported in "
                      f"live mode (use integer index): {conn!r}", file=sys.stderr)
                errors += 1
                continue
            args["target_input_index"] = dst_pin or 0
        else:
            print(f"  skip: target {dst_name!r} is neither a node nor a known root input",
                  file=sys.stderr)
            errors += 1
            continue
        try:
            bridge.call("connect_material_pins", args)
            print(f"  connect {conn}")
        except Exception as e:
            print(f"  fail: {conn} — {e}", file=sys.stderr)
            errors += 1

    archive_yaml(yaml_path)
    print(f"[live] done — {material_path} ({errors} connection error(s))")
    return 1 if errors else 0


def apply_clipboard(yaml_path: Path, output: Path | None) -> int:
    generator = PLUGIN_DIR / "ue5_material_generator.py"
    cmd = [sys.executable, str(generator), str(yaml_path)]
    if output:
        cmd += ["-o", str(output)]
    print(f"[clipboard] {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    archive_yaml(yaml_path)
    return result.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="YAML → UE5 material.")
    p.add_argument("yaml", help="Path to the YAML spec")
    p.add_argument("--mode", choices=["auto", "live", "clipboard"], default="auto")
    p.add_argument("-o", "--output", help="Clipboard mode: write T3D to this file")
    args = p.parse_args()

    yaml_path = Path(args.yaml).resolve()
    if not yaml_path.exists():
        print(f"file not found: {yaml_path}", file=sys.stderr)
        return 1
    spec = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    mode = args.mode
    if mode == "auto":
        mode = "live" if bridge.is_alive() else "clipboard"
        print(f"[auto] bridge {'alive' if mode == 'live' else 'unreachable'} "
              f"→ {mode} mode", file=sys.stderr)

    if mode == "live":
        return apply_live(spec, yaml_path)
    return apply_clipboard(yaml_path, Path(args.output) if args.output else None)


if __name__ == "__main__":
    sys.exit(main())
