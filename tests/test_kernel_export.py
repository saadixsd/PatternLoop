from pathlib import Path

import yaml

from patternloop.config import AppConfig
from patternloop.inference import MockBackend
from patternloop.kernel import run_pattern
from patternloop.loopspec import LoopSpec, SuccessCheck, save_loopspec
from patternloop.tools.registry import ToolRegistry
from patternloop.tools.sandbox import FileSandbox


def test_kernel_mock_success(tmp_path: Path) -> None:
    spec = LoopSpec(
        name="t",
        goal_template="{goal}",
        system_prompt="sys",
        planner_prompt="plan",
        evaluator_prompt="Reply JSON only: {\"score\": 1, \"reason\": \"ok\"}",
        success=SuccessCheck(min_output_chars=1),
    )
    spec_path = tmp_path / "t.yaml"
    save_loopspec(spec_path, spec)

    cfg = AppConfig()
    sandbox = FileSandbox([tmp_path])
    reg = ToolRegistry(sandbox)
    backend = MockBackend(
        replies=[
            "FINAL: hello world answer",
            '{"score": 1, "reason": "ok"}',
        ]
    )
    res = run_pattern(
        spec=spec,
        goal="g",
        backend=backend,
        registry=reg,
        cfg=cfg,
        pattern_path=spec_path,
    )
    assert res.ok
    assert res.answer


def test_export_roundtrip(tmp_path: Path) -> None:
    from patternloop.export import build_agent_bundle, import_agent_bundle

    spec = LoopSpec(
        name="imp",
        goal_template="{goal}",
        system_prompt="s",
        planner_prompt="p",
        evaluator_prompt="e",
    )
    p = tmp_path / "imp.yaml"
    save_loopspec(p, spec)
    z = tmp_path / "out.agent"
    build_agent_bundle(spec_path=p, out_path=z)
    dest = tmp_path / "patterns"
    dest.mkdir()
    final = import_agent_bundle(zip_path=z, dest_dir=dest)
    assert final.exists()
    data = yaml.safe_load(final.read_text())
    assert data["name"] == "imp"
