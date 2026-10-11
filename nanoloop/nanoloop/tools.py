"""Tools: a safe calculator, a small tool registry, and a constrained decoder
that makes every emitted tool call structurally valid.

What a ~200M model can realistically do (docs/RESEARCH.md §7): pick one of a
small, fixed tool set and fill a few arguments, on phrasing close to its
finetuning data. Constrained decoding is mandatory at this size; it turns
"almost JSON" into a call that always parses and always names a real tool.
"""

from __future__ import annotations

import ast
import json
import math
import operator
from dataclasses import dataclass, field
from typing import Callable

# ----------------------------------------------------------------------------
# Calculator (used inline for math and as a regular tool)
# ----------------------------------------------------------------------------

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_UN = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
        return _UN[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def format_number(x) -> str:
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError("non-finite")
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
        return f"{x:.6f}".rstrip("0").rstrip(".")
    return str(x)


def calculate(expr: str) -> str:
    """Arithmetic only (+ - * / // % and parentheses; no powers, names or
    calls). Returns the result as text, or 'error'."""
    expr = expr.strip().replace(",", "").replace("x", "*").replace("×", "*").replace("÷", "/")
    if not expr or len(expr) > 120:
        return "error"
    try:
        return format_number(_eval(ast.parse(expr, mode="eval")))
    except Exception:
        return "error"


# ----------------------------------------------------------------------------
# Tool registry
# ----------------------------------------------------------------------------


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON-schema "properties" -> {"type": ..., "description": ...}
    fn: Callable = field(repr=False, default=None)
    required: list | None = None

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description,
                "parameters": {"type": "object", "properties": self.parameters,
                               "required": self.required or list(self.parameters)}}

    def __call__(self, **kwargs):
        return self.fn(**kwargs)


def _convert_units(value, from_unit, to_unit):
    table = {("km", "mi"): 0.621371, ("mi", "km"): 1.609344, ("kg", "lb"): 2.204623,
             ("lb", "kg"): 0.453592, ("m", "ft"): 3.28084, ("ft", "m"): 0.3048,
             ("l", "gal"): 0.264172, ("gal", "l"): 3.785412}
    f, t = str(from_unit).lower(), str(to_unit).lower()
    if (f, t) in (("c", "f"), ("celsius", "fahrenheit")):
        return format_number(float(value) * 9 / 5 + 32)
    if (f, t) in (("f", "c"), ("fahrenheit", "celsius")):
        return format_number((float(value) - 32) * 5 / 9)
    if (f, t) not in table:
        return f"error: cannot convert {f} to {t}"
    return format_number(round(float(value) * table[(f, t)], 4))


BUILTIN_TOOLS = {
    "calculator": Tool("calculator", "Evaluate an arithmetic expression.",
                       {"expression": {"type": "string", "description": "e.g. (12+30)*4/3"}},
                       fn=lambda expression: calculate(expression)),
    "convert_units": Tool("convert_units", "Convert a value between units (km, mi, kg, lb, m, ft, l, gal, c, f).",
                          {"value": {"type": "number"}, "from_unit": {"type": "string"},
                           "to_unit": {"type": "string"}}, fn=_convert_units),
    "word_count": Tool("word_count", "Count the words in a text.",
                       {"text": {"type": "string"}}, fn=lambda text: str(len(str(text).split()))),
}


def tools_system_prompt(tools) -> str:
    specs = "\n".join(json.dumps(t.schema(), separators=(",", ":")) for t in tools)
    return ("You can call these tools. To call one, reply with a tool call; otherwise answer directly.\n"
            + specs)


def run_tool_call(call: dict, tools: dict) -> str:
    tool = tools.get(call.get("name"))
    if tool is None:
        return f"error: unknown tool {call.get('name')!r}"
    try:
        return str(tool(**(call.get("arguments") or {})))
    except Exception as e:  # report, don't crash the agent loop
        return f"error: {type(e).__name__}"


# ----------------------------------------------------------------------------
# JSON-prefix validation (for constrained decoding of tool-call arguments)
# ----------------------------------------------------------------------------


def json_prefix_state(s: str):
    """Character-level scan of s as the prefix of ONE JSON value. Returns
    (ok, complete): ok is False as soon as s cannot be extended into valid
    JSON; complete is True when s is exactly one finished JSON value."""
    st = _scan(s)
    return st[0], st[1]


def json_close(s: str) -> str:
    """Shortest-ish suffix that turns a valid JSON prefix into a complete value
    (used when a tool call's arguments run past their budget)."""
    ok, complete, mode, stack, buf, lit, li = _scan(s)
    if not ok:
        raise ValueError("not a JSON prefix")
    if complete:
        return ""
    out = ""
    if mode == "STR":
        out += '"'
    elif mode == "KSTR":
        out += '":null'
    elif mode == "NUM":
        out += "0" if not _is_num(buf) else ""
    elif mode == "LIT":
        out += lit[li:]
    elif mode == "COLON":
        out += ":null"
    elif mode == "VALUE":
        out += "null" if stack else "{}"
    elif mode == "KEY":
        out += '"_":null'
    for c in reversed(stack):
        out += "}" if c == "o" else "]"
    return out


def _scan(s: str):
    stack = []          # open containers: "o" object / "a" array
    mode = "VALUE"      # VALUE VALUE_OR_END KEY KEY_OR_END COLON COMMA_OR_END STR KSTR NUM LIT DONE
    esc, buf, lit, li = False, "", "", 0

    def after_value():
        return "COMMA_OR_END" if stack else "DONE"

    for c in s:
        if mode in ("STR", "KSTR"):
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                mode = "COLON" if mode == "KSTR" else after_value()
            elif ord(c) < 0x20:
                return False, False, None, None, None, None, None, None, None, None, None, None
            continue
        if mode == "NUM":
            if c in "0123456789.eE+-":
                buf += c
                if not _num_prefix(buf):
                    return False, False, None, None, None, None, None, None, None, None, None, None
                continue
            if not _is_num(buf):
                return False, False, None, None, None, None, None, None, None, None, None, None
            mode = after_value()  # and fall through to handle c
        if mode == "LIT":
            if c != lit[li]:
                return False, False, None, None, None, None, None, None, None, None, None, None
            li += 1
            if li == len(lit):
                mode = after_value()
            continue
        if c in " \t\n\r":
            continue
        if mode == "DONE":
            return False, False, None, None, None, None, None
        if mode in ("VALUE", "VALUE_OR_END"):
            if mode == "VALUE_OR_END" and c == "]":
                stack.pop()
                mode = after_value()
            elif c == "{":
                stack.append("o")
                mode = "KEY_OR_END"
            elif c == "[":
                stack.append("a")
                mode = "VALUE_OR_END"
            elif c == '"':
                mode = "STR"
            elif c in "-0123456789":
                mode, buf = "NUM", c
            elif c in "tfn":
                mode, lit, li = "LIT", {"t": "true", "f": "false", "n": "null"}[c], 1
            else:
                return False, False, None, None, None, None, None, None, None, None, None, None
        elif mode in ("KEY", "KEY_OR_END"):
            if mode == "KEY_OR_END" and c == "}":
                stack.pop()
                mode = after_value()
            elif c == '"':
                mode = "KSTR"
            else:
                return False, False, None, None, None, None, None, None, None, None, None, None
        elif mode == "COLON":
            if c != ":":
                return False, False, None, None, None, None, None, None, None, None, None, None
            mode = "VALUE"
        elif mode == "COMMA_OR_END":
            top = stack[-1]
            if c == ",":
                mode = "KEY" if top == "o" else "VALUE"
            elif (c == "}" and top == "o") or (c == "]" and top == "a"):
                stack.pop()
                mode = after_value()
            else:
                return False, False, None, None, None, None, None, None, None, None, None, None
    complete = mode == "DONE" or (mode == "NUM" and not stack and _is_num(buf))
    return True, complete, mode, stack, buf, lit, li


def _is_num(t):
    try:
        json.loads(t)
        return True
    except ValueError:
        return False


def _num_prefix(t):
    return _is_num(t) or _is_num(t + "0") or _is_num(t + "1") or t == "-"
