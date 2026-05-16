"""Resolve PatternLoop home and standard subdirectories."""

from __future__ import annotations

import os
from pathlib import Path


def patternloop_home() -> Path:
    if os.environ.get("PATTERNLOOP_HOME"):
        return Path(os.environ["PATTERNLOOP_HOME"]).expanduser().resolve()
    # XDG-like default next to config if set
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return (Path(xdg) / "patternloop").resolve()
    return Path.home() / ".patternloop"


def ensure_layout(root: Path | None = None) -> dict[str, Path]:
    base = root or patternloop_home()
    sub = {
        "root": base,
        "patterns": base / "patterns",
        "runs": base / "runs",
        "memory": base / "memory",
        "connectors": base / "connectors",
        "exports": base / "exports",
    }
    for p in sub.values():
        p.mkdir(parents=True, exist_ok=True)
    return sub
