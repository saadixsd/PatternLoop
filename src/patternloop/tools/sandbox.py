"""Read-only filesystem tools within allowlisted roots."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool
    tool: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


class FileSandbox:
    def __init__(self, read_roots: list[Path], allow_write: bool = False) -> None:
        self.read_roots = [r.resolve() for r in read_roots]
        self.allow_write = allow_write

    def _resolve_allowed(self, rel_or_abs: str) -> Path:
        p = Path(rel_or_abs).expanduser()
        if not p.is_absolute():
            if len(self.read_roots) != 1:
                raise ValueError("Relative paths require exactly one read root")
            p = (self.read_roots[0] / p).resolve()
        else:
            p = p.resolve()
        allowed = False
        for root in self.read_roots:
            try:
                p.relative_to(root)
                allowed = True
                break
            except ValueError:
                continue
        if not allowed:
            raise PermissionError(f"Path not in allowlist: {p}")
        return p

    def read_file(self, path: str, max_bytes: int = 200_000) -> ToolResult:
        try:
            p = self._resolve_allowed(path)
            if not p.is_file():
                return ToolResult(ok=False, tool="read_file", detail="not a file", data={})
            data = p.read_bytes()
            if len(data) > max_bytes:
                text = data[:max_bytes].decode("utf-8", errors="replace") + "\n...[truncated]"
            else:
                text = data.decode("utf-8", errors="replace")
            return ToolResult(ok=True, tool="read_file", detail="ok", data={"path": str(p), "content": text})
        except Exception as e:
            return ToolResult(ok=False, tool="read_file", detail=str(e), data={})

    def list_dir(self, path: str) -> ToolResult:
        try:
            p = self._resolve_allowed(path)
            if not p.is_dir():
                return ToolResult(ok=False, tool="list_dir", detail="not a directory", data={})
            entries = sorted(os.listdir(p))
            return ToolResult(ok=True, tool="list_dir", detail="ok", data={"path": str(p), "entries": entries})
        except Exception as e:
            return ToolResult(ok=False, tool="list_dir", detail=str(e), data={})
