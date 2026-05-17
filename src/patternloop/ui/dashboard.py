"""Local Gradio dashboard (binds to 127.0.0.1 by default)."""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from patternloop.config import default_config_path, load_config
from patternloop.export import build_agent_bundle
from patternloop.inference import MockBackend, OllamaBackend
from patternloop.kernel import run_pattern
from patternloop.loopspec import load_loopspec
from patternloop.memory import EpisodicMemory
from patternloop.paths import ensure_layout
from patternloop.tools.registry import ToolRegistry
from patternloop.tools.sandbox import FileSandbox


def _default_workdir() -> str:
    demo = Path.cwd() / "examples" / "demo_notes"
    if demo.is_dir():
        return str(demo.resolve())
    return str(Path.home())


def launch_dashboard(host: str = "127.0.0.1", port: int = 7860) -> None:
    layout = ensure_layout()
    cfg_path = default_config_path(layout["root"])
    cfg = load_config(cfg_path)

    def run_fn(pattern_name: str, goal: str, workdir: str, mock: bool) -> str:
        p = layout["patterns"] / f"{pattern_name}.yaml"
        if not p.exists():
            return f"Pattern not found: {p}"
        spec = load_loopspec(p)
        roots = [Path(workdir).expanduser().resolve()]
        sandbox = FileSandbox(roots, allow_write=cfg.tools.allow_write)
        registry = ToolRegistry(sandbox)
        if mock:
            backend = MockBackend(
                replies=[
                    'TOOL_CALL: {"name": "list_dir", "arguments": {"path": "."}}',
                    "FINAL: Demo answer for PatternLoop dashboard (mock).",
                ]
            )
        else:
            backend = OllamaBackend(
                cfg.ollama.base_url, cfg.ollama.model, timeout=cfg.ollama.timeout_seconds
            )
        mem = EpisodicMemory(layout["memory"] / "episodes.sqlite3")
        res = run_pattern(
            spec=spec,
            goal=goal,
            backend=backend,
            registry=registry,
            cfg=cfg,
            memory=mem,
            pattern_path=p,
            kill_file=layout["root"] / "KILL",
        )
        mem.close()
        return f"ok={res.ok}\nanswer={res.answer}\nscores={res.state.scores}"

    def export_fn(pattern_name: str) -> str:
        p = layout["patterns"] / f"{pattern_name}.yaml"
        if not p.exists():
            return f"missing: {p}"
        out = layout["exports"] / f"{pattern_name}.agent"
        build_agent_bundle(spec_path=p, out_path=out)
        return str(out)

    with gr.Blocks(title="PatternLoop") as demo:
        gr.Markdown("# PatternLoop (local)")
        with gr.Row():
            pattern = gr.Textbox(label="Pattern name", value="research_digest")
            goal = gr.Textbox(label="Goal", value="Summarize themes; cite filenames.")
            workdir = gr.Textbox(label="Workdir (allowlisted)", value=_default_workdir())
        mock = gr.Checkbox(label="Mock backend (no Ollama)", value=False)
        out = gr.Textbox(label="Output", lines=16)
        run_btn = gr.Button("Run")
        run_btn.click(run_fn, inputs=[pattern, goal, workdir, mock], outputs=out)

        export_pattern = gr.Textbox(label="Export pattern", value="research_digest")
        export_out = gr.Textbox(label="Export path")
        export_btn = gr.Button("Export .agent")
        export_btn.click(export_fn, inputs=[export_pattern], outputs=export_out)

    url = f"http://{host}:{port}/"
    print(f"PatternLoop UI loading (Gradio may take 30-60s on first start)...", flush=True)
    print(f"Open in browser when ready: {url}", flush=True)
    print("Leave this terminal open. Press Ctrl+C to stop.", flush=True)
    demo.launch(server_name=host, server_port=port, share=False, show_error=True)
