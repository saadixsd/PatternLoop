"""Tool registry — maps tool names to sandbox operations."""

from __future__ import annotations

import json
import re
from typing import Any

from patternloop.tools.sandbox import FileSandbox, ToolResult

# Placeholder import for typing
JsonDict = dict[str, Any]


class ToolRegistry:
    def __init__(self, sandbox: FileSandbox | None = None) -> None:
        self.sandbox = sandbox

    def call(self, name: str, arguments: JsonDict) -> ToolResult:
        if self.sandbox is None:
            return ToolResult(ok=False, tool=name, detail="sandbox disabled", data={})
        if name == "read_file":
            return self.sandbox.read_file(str(arguments.get("path", "")))
        if name == "list_dir":
            return self.sandbox.list_dir(str(arguments.get("path", ".")))
        return ToolResult(ok=False, tool=name, detail=f"unknown tool: {name}", data={})


def tools_schema_for_ollama() -> list[dict[str, Any]]:
    """Minimal JSON-schema style descriptions for prompt embedding."""

    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file within allowed roots",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List directory entries within allowed roots",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
    ]


def parse_tool_call_json(text: str) -> tuple[str | None, dict[str, Any] | None]:
    """Extract tool call from model output; expects TOOL_CALL: {...} on a line (markdown bold tolerated)."""

    # Models often wrap the trigger as **TOOL_CALL:** {...}
    line_pat = re.compile(r"^\*{0,}TOOL_CALL:\*{0,}\s*(\{.*\})\s*$", re.IGNORECASE)
    for raw in text.splitlines():
        line = raw.strip().strip("*").strip()
        m = line_pat.search(line)
        if not m:
            continue
        payload = m.group(1)
        try:
            obj = json.loads(payload)
            name = obj.get("name")
            args = obj.get("arguments") or {}
            if isinstance(name, str) and isinstance(args, dict):
                return name, args
        except json.JSONDecodeError:
            return None, None
    return None, None
