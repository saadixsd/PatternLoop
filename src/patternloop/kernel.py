"""Execution kernel — plan/act/evaluate/adapt loop."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from patternloop.config import AppConfig, Limits
from patternloop.inference import InferenceBackend
from patternloop.logging_setup import safe_json
from patternloop.loopspec import LoopSpec, save_loopspec
from patternloop.memory import EpisodicMemory
from patternloop.tools.registry import ToolRegistry, parse_tool_call_json

log = logging.getLogger(__name__)


@dataclass
class RunState:
    run_id: str
    pattern: str
    messages: list[str] = field(default_factory=list)
    tool_calls_used: int = 0
    iterations: int = 0
    final_answer: str | None = None
    scores: list[float] = field(default_factory=list)


def _goal_text(spec: LoopSpec, goal: str) -> str:
    return spec.goal_template.replace("{goal}", goal)


def _extract_final(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip().upper().startswith("FINAL:"):
            return line.split(":", 1)[1].strip()
    return None


def _extract_eval_score(text: str) -> tuple[float, str]:
    try:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            obj = json.loads(m.group(0))
            score = float(obj.get("score", 0.0))
            reason = str(obj.get("reason", ""))
            return max(0.0, min(1.0, score)), reason
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return 0.0, "unparseable evaluator output"


def _success_check(spec: LoopSpec, answer: str) -> bool:
    if len(answer) < spec.success.min_output_chars:
        return False
    if not spec.success.keywords:
        return True
    lower = answer.lower()
    return all(k.lower() in lower for k in spec.success.keywords)


def _list_dir_coverage(messages: list[str]) -> tuple[bool, set[str], set[str]]:
    """Whether reads are pending, wanted basenames from latest good list_dir, basenames read ok after it."""

    last_good_idx: int | None = None
    entries: list[str] = []
    for i, m in enumerate(messages):
        if not m.startswith("tool:list_dir ->"):
            continue
        try:
            obj = json.loads(m.split("->", 1)[1].strip())
        except (json.JSONDecodeError, TypeError, IndexError):
            continue
        if not obj.get("ok"):
            continue
        ent = (obj.get("data") or {}).get("entries")
        if isinstance(ent, list) and len(ent) > 0:
            last_good_idx = i
            entries = [str(x) for x in ent]
    if last_good_idx is None:
        return False, set(), set()

    want = {Path(e).name for e in entries}
    read_names: set[str] = set()
    for m in messages[last_good_idx + 1 :]:
        if not m.startswith("tool:read_file ->"):
            continue
        try:
            robj = json.loads(m.split("->", 1)[1].strip())
        except (json.JSONDecodeError, TypeError, IndexError):
            continue
        if not robj.get("ok"):
            continue
        p = (robj.get("data") or {}).get("path")
        if isinstance(p, str):
            read_names.add(Path(p).name)

    pending = not want.issubset(read_names)
    return pending, want, read_names




@dataclass
class RunResult:
    ok: bool
    answer: str | None
    state: RunState
    adapted_spec_path: Path | None


def run_pattern(
    *,
    spec: LoopSpec,
    goal: str,
    backend: InferenceBackend,
    registry: ToolRegistry,
    cfg: AppConfig,
    memory: EpisodicMemory | None = None,
    pattern_path: Path | None = None,
    kill_file: Path | None = None,
) -> RunResult:
    lim_dict = cfg.limits.model_dump()
    for k, v in (spec.limits_override or {}).items():
        if k in lim_dict:
            lim_dict[k] = v
    limits = Limits.model_validate(lim_dict)

    run_id = str(uuid.uuid4())
    state = RunState(run_id=run_id, pattern=spec.name)
    goal_str = _goal_text(spec, goal)
    adapted_path: Path | None = None
    planner_hint = ""

    start = time.monotonic()
    adaptation_edits = 0

    while state.iterations < limits.max_iterations:
        if kill_file and kill_file.exists():
            state.messages.append("ABORT: kill switch file present")
            break
        if time.monotonic() - start > limits.wall_seconds:
            state.messages.append("ABORT: wall clock limit")
            break
        state.iterations += 1

        tools_doc = (
            "Available tools: read_file, list_dir. "
            "Emit at most one TOOL_CALL per assistant message as: "
            'TOOL_CALL: {"name": "read_file", "arguments": {"path": "..."}}\n'
            'Paths must stay inside the user work directory only: start with list_dir on "." '
            'then read_file each entry name you saw (for example "notes.txt"). '
            "Do not invent absolute paths or folders like /allowed/.\n"
            "After a successful list_dir, your very next message must be exactly one "
            'TOOL_CALL read_file for one filename from that entries list (exact spelling); '
            "then alternate tool calls until all relevant text files are read.\n"
            "When done, emit a line starting with FINAL:"
        )
        user = (
            f"{spec.planner_prompt}\n\n{tools_doc}\n\nGoal:\n{goal_str}\n\n"
            f"Prior transcript:\n" + "\n".join(state.messages[-16:]) + f"\n{planner_hint}"
        )
        assistant = backend.generate(spec.system_prompt, user, temperature=0.3)
        state.messages.append(f"assistant: {assistant}")
        if memory:
            memory.append(run_id, "assistant", {"text": assistant, "pattern": spec.name})

        tool_name, tool_args = parse_tool_call_json(assistant)
        if tool_name and state.tool_calls_used < limits.max_tool_calls:
            state.tool_calls_used += 1
            res = registry.call(tool_name, tool_args or {})
            state.messages.append(f"tool:{tool_name} -> {safe_json(res.model_dump())}")
            if memory:
                memory.append(run_id, "tool", {"name": tool_name, "result": res.model_dump()})
            continue

        pending_reads, want, read_ok = _list_dir_coverage(state.messages)
        if pending_reads:
            missing = sorted(want - read_ok)
            state.messages.append(
                "system: list_dir is complete. Read every remaining file using exact names "
                f"(copy/paste): {missing}. One TOOL_CALL read_file per message; do not invent names."
            )
            continue

        candidate = _extract_final(assistant) or assistant.strip()
        eval_user = (
            f"{spec.evaluator_prompt}\n\nGoal:\n{goal_str}\n\nCandidate:\n{candidate}\n"
        )
        eval_out = backend.generate(
            "You output compact JSON with score and reason only.",
            eval_user,
            temperature=0.0,
        )
        score, reason = _extract_eval_score(eval_out)
        state.scores.append(score)
        state.messages.append(f"eval: score={score} reason={reason}")

        if memory:
            memory.append(
                run_id,
                "eval",
                {"score": score, "reason": reason, "pattern": spec.name},
            )

        if score >= 0.75 and _success_check(spec, candidate):
            state.final_answer = candidate
            return RunResult(ok=True, answer=candidate, state=state, adapted_spec_path=None)

        # Adaptation: append hint to planner; optionally bump temperature via hint
        if adaptation_edits < spec.adaptation.max_prompt_edits_per_run:
            adaptation_edits += 1
            planner_hint = (
                f"\n(Hint: previous attempt scored {score}. Improve structure and groundedness. {reason})\n"
            )
            if memory:
                memory.append(run_id, "adapt", {"hint": planner_hint})

    # No success — save adapted spec optional small tweak
    if pattern_path and adaptation_edits:
        new_spec = spec.model_copy(
            update={
                "planner_prompt": spec.planner_prompt
                + "\nPrefer concise FINAL answers with clear sections.",
                "parent_hash": spec.hash(),
            }
        )
        adapted_path = pattern_path.with_name(pattern_path.stem + "_adapted.yaml")
        save_loopspec(adapted_path, new_spec)

    return RunResult(
        ok=False,
        answer=state.final_answer,
        state=state,
        adapted_spec_path=adapted_path,
    )
