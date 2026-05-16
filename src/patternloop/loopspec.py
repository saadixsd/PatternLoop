"""LoopSpec v1 — versioned artifact describing a runnable pattern loop."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SuccessCheck(BaseModel):
    """Declarative checks; kernel interprets known kinds."""

    kind: str = "keywords"
    keywords: list[str] = Field(default_factory=list)
    min_output_chars: int = 0


class AdaptationHooks(BaseModel):
    """Bounds for prompt deltas applied after failed evaluations."""

    max_prompt_edits_per_run: int = 3
    temperature_steps: list[float] = Field(default_factory=lambda: [0.2, 0.4])


class ToolEntry(BaseModel):
    name: str
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class LoopSpec(BaseModel):
    version: int = 1
    name: str
    goal_template: str
    system_prompt: str
    planner_prompt: str
    evaluator_prompt: str
    tools: list[ToolEntry] = Field(default_factory=list)
    success: SuccessCheck = Field(default_factory=SuccessCheck)
    adaptation: AdaptationHooks = Field(default_factory=AdaptationHooks)
    limits_override: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)
    parent_hash: str | None = None

    def content_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d.pop("meta", None)
        return d

    def hash(self) -> str:
        payload = json.dumps(self.content_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def save_loopspec(path: Path, spec: LoopSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(spec.meta)
    meta.setdefault("saved_at", utc_now_iso())
    meta.setdefault("content_sha256", spec.hash())
    out = spec.model_copy(update={"meta": meta})
    path.write_text(
        yaml.safe_dump(out.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def load_loopspec(path: Path) -> LoopSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return LoopSpec.model_validate(raw)


def new_pattern_id() -> str:
    return str(uuid.uuid4())
