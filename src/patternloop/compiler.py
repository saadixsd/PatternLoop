"""Compile example traces and goals into a LoopSpec draft."""

from __future__ import annotations

import json
import re
from pathlib import Path

from patternloop.inference import InferenceBackend
from patternloop.loopspec import LoopSpec, SuccessCheck, ToolEntry

COMPILER_SYSTEM = (
    "You are the PatternLoop compiler. Output ONLY valid JSON matching this shape:\n"
    "{\n"
    '  "name": "short_snake_name",\n'
    '  "goal_template": "Instructions; include the literal token {goal} '
    'where the live goal string should go.",\n'
    '  "system_prompt": "...",\n'
    '  "planner_prompt": "Act stepwise; when using a tool output one line: '
    "TOOL_CALL: {\\\"name\\\": \\\"read_file\\\", \\\"arguments\\\": "
    '{\\\"path\\\": \\\"relative/path\\\"}}\\nWhen finished output: FINAL: your answer",\n'
    '  "evaluator_prompt": "Score candidate vs goal 0..1. Reply JSON only: '
    '{\\\"score\\\": 0.8, \\\"reason\\\": \\\"...\\\"}",\n'
    '  "tools": [{"name": "read_file", "enabled": true}, '
    '{"name": "list_dir", "enabled": true}],\n'
    '  "success": {"kind": "keywords", "keywords": [], "min_output_chars": 50}\n'
    "}\n"
    "No markdown fences, no commentary. The token must appear exactly as {goal} "
    "inside goal_template string."
)


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in compiler output")
    return json.loads(m.group(0))


def compile_from_traces(
    *,
    backend: InferenceBackend,
    name: str,
    goal: str,
    traces: list[str],
    temperature: float = 0.1,
) -> LoopSpec:
    joined = "\n---\n".join(traces[:10])
    user = (
        f"Agent name: {name}\n"
        f"Compile a LoopSpec. Example user goal for calibration:\n{goal}\n\n"
        f"Example traces (user-redacted):\n{joined}\n"
    )
    raw = backend.generate(COMPILER_SYSTEM, user, temperature=temperature)
    data = _extract_json_object(raw)
    data.setdefault("name", name)
    gt = str(data.get("goal_template", "{goal}"))
    if "{goal}" not in gt:
        gt = "{goal}\n" + gt

    tools_raw = data.get("tools") or [
        {"name": "read_file", "enabled": True},
        {"name": "list_dir", "enabled": True},
    ]
    tools = [ToolEntry.model_validate(t) for t in tools_raw]

    succ_raw = data.get("success") if isinstance(data.get("success"), dict) else {}
    success = SuccessCheck.model_validate(succ_raw)

    return LoopSpec(
        name=str(data.get("name", name)),
        goal_template=gt,
        system_prompt=str(data.get("system_prompt", "You are a careful assistant.")),
        planner_prompt=str(
            data.get(
                "planner_prompt",
                "Use read_file/list_dir within allowed roots. One tool call per turn as TOOL_CALL JSON line.",
            )
        ),
        evaluator_prompt=str(
            data.get(
                "evaluator_prompt",
                'Score 0..1. Reply JSON only: {"score": 0.8, "reason": "..."}',
            )
        ),
        tools=tools,
        success=success,
    )


def load_traces_from_paths(paths: list[Path]) -> list[str]:
    out: list[str] = []
    for p in paths:
        out.append(p.read_text(encoding="utf-8", errors="replace")[:50_000])
    return out
