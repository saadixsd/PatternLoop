"""Typer CLI for PatternLoop."""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console

from patternloop import __version__
from patternloop.compiler import compile_from_traces, load_traces_from_paths
from patternloop.config import AppConfig, default_config_path, load_config, save_config
from patternloop.connectors import ClaudeBackend
from patternloop.connectors.n8n import trigger_n8n_webhook
from patternloop.export import build_agent_bundle, import_agent_bundle
from patternloop.inference import MockBackend, OllamaBackend
from patternloop.kernel import run_pattern
from patternloop.logging_setup import redact_text, setup_logging
from patternloop.loopspec import load_loopspec, new_pattern_id, save_loopspec
from patternloop.memory import EpisodicMemory
from patternloop.paths import ensure_layout
from patternloop.tools.registry import ToolRegistry
from patternloop.tools.sandbox import FileSandbox

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
agents_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(agents_app, name="agents")


def _bundled_root():
    return importlib.resources.files("patternloop") / "bundled"


def bundled_spec_trav(name: str):
    return _bundled_root() / f"{name}.yaml"

def _resolve_backend(cfg: AppConfig, mock: bool):
    if mock:
        return MockBackend()
    if cfg.connectors.claude.enabled:
        return ClaudeBackend(
            model=cfg.connectors.claude.model,
            max_tokens=cfg.connectors.claude.max_tokens,
        )
    return OllamaBackend(
        cfg.ollama.base_url,
        cfg.ollama.model,
        timeout=cfg.ollama.timeout_seconds,
    )


@app.command()
def init(
    home: Annotated[
        Path | None,
        typer.Option(help="Override data directory (default ~/.patternloop)"),
    ] = None,
) -> None:
    """Create data dirs and a starter config.yaml."""

    if home:
        import os

        os.environ["PATTERNLOOP_HOME"] = str(home.expanduser().resolve())
    layout = ensure_layout()
    cfg_path = default_config_path(layout["root"])
    if not cfg_path.exists():
        save_config(cfg_path, AppConfig())
        console.print(f"[green]Wrote[/green] {cfg_path}")
    else:
        console.print(f"[yellow]Exists[/yellow] {cfg_path}")
    console.print(f"Data root: [bold]{layout['root']}[/bold]")


@app.command("compile")
def compile_cmd(
    name: str,
    goal: str,
    trace: Annotated[
        list[Path],
        typer.Option(
            "--trace",
            exists=True,
            readable=True,
            help="Example trace file (repeatable).",
        ),
    ],
    mock: bool = False,
) -> None:
    """Compile trace files into a LoopSpec (draft) via local LLM."""

    if not trace:
        raise typer.BadParameter("Provide at least one --trace file.")
    setup_logging()
    layout = ensure_layout()
    cfg = load_config(default_config_path(layout["root"]))
    backend = _resolve_backend(cfg, mock=mock)
    traces = load_traces_from_paths(trace)
    spec = compile_from_traces(backend=backend, name=name, goal=goal, traces=traces)
    spec.meta.setdefault("id", new_pattern_id())
    dest = layout["patterns"] / f"{name}.yaml"
    save_loopspec(dest, spec)
    console.print(redact_text(f"Saved LoopSpec to {dest} hash={spec.hash()}"))


@app.command("run")
def run_cmd(
    pattern: str,
    goal: str,
    workdir: Annotated[Path, typer.Option(exists=True, file_okay=False, resolve_path=True)],
    mock: bool = False,
) -> None:
    """Run a LoopSpec against a goal with tools scoped to workdir."""

    setup_logging()
    layout = ensure_layout()
    cfg = load_config(default_config_path(layout["root"]))
    cfg.tools.read_roots = [str(workdir)]
    pattern_path = layout["patterns"] / f"{pattern}.yaml"
    if not pattern_path.exists():
        raise typer.BadParameter(f"Unknown pattern: {pattern_path}")

    spec = load_loopspec(pattern_path)
    sandbox = FileSandbox([workdir], allow_write=cfg.tools.allow_write)
    registry = ToolRegistry(sandbox)
    backend = _resolve_backend(cfg, mock=mock)
    mem = EpisodicMemory(layout["memory"] / "episodes.sqlite3")
    kill_file = layout["root"] / "KILL"
    res = run_pattern(
        spec=spec,
        goal=goal,
        backend=backend,
        registry=registry,
        cfg=cfg,
        memory=mem,
        pattern_path=pattern_path,
        kill_file=kill_file,
    )
    mem.close()
    log_path = layout["runs"] / f"{res.state.run_id}.yaml"
    log_path.write_text(yaml.safe_dump({"messages": res.state.messages, "scores": res.state.scores}))
    console.print(redact_text(f"ok={res.ok} answer={res.answer} adapted={res.adapted_spec_path}"))
    console.print(f"run log: {log_path}")


@agents_app.command("list")
def agents_list() -> None:
    """List bundled and installed patterns."""

    layout = ensure_layout()
    installed = sorted(layout["patterns"].glob("*.yaml"))
    root = _bundled_root()
    console.print("[bold]Bundled[/bold]")
    for item in sorted(root.iterdir(), key=lambda x: x.name):
        if item.name.endswith(".yaml"):
            console.print(f"  - {Path(item.name).stem}")
    console.print("[bold]Installed[/bold]")
    for p in installed:
        console.print(f"  - {p.stem}")


@agents_app.command("install")
def agents_install(
    name: str,
    yes: bool = False,
) -> None:
    """Copy a bundled LoopSpec into the user patterns directory."""

    src_trav = bundled_spec_trav(name)
    if not src_trav.is_file():
        raise typer.BadParameter(f"No bundled agent {name}")
    layout = ensure_layout()
    dest = layout["patterns"] / f"{name}.yaml"
    if dest.exists() and not yes:
        raise typer.BadParameter(f"{dest} exists; pass --yes to overwrite")
    with importlib.resources.as_file(src_trav) as src:
        shutil.copy(src, dest)
    console.print(f"Installed {name} -> {dest}")


@app.command()
def export(
    pattern: str,
    out: Path | None = None,
) -> None:
    """Export a pattern to a .agent zip."""

    layout = ensure_layout()
    spec_path = layout["patterns"] / f"{pattern}.yaml"
    if not spec_path.exists():
        raise typer.BadParameter(str(spec_path))
    out_path = out or (layout["exports"] / f"{pattern}.agent")
    build_agent_bundle(spec_path=spec_path, out_path=out_path)
    console.print(str(out_path))


@app.command("import-bundle")
def import_bundle_cmd(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
) -> None:
    """Import a .agent bundle into installed patterns."""

    layout = ensure_layout()
    final = import_agent_bundle(zip_path=path, dest_dir=layout["patterns"])
    console.print(f"Imported -> {final}")


@app.command()
def n8n_ping(
    url: str,
    payload_json: str = "{}",
) -> None:
    """POST JSON to an n8n webhook (requires connector secret if configured)."""

    layout = ensure_layout()
    cfg = load_config(default_config_path(layout["root"]))
    if not cfg.connectors.n8n.enabled:
        console.print("[yellow]connectors.n8n.enabled is false in config[/yellow]")
    import json

    data = json.loads(payload_json)
    res = trigger_n8n_webhook(
        url=url,
        payload=data,
        secret_env=cfg.connectors.n8n.hmac_secret_env,
    )
    console.print(redact_text(str(res)))


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 7860,
) -> None:
    """Launch the local Gradio dashboard."""

    from patternloop.ui.dashboard import launch_dashboard

    console.print(f"[bold]Starting UI[/bold] at http://{host}:{port}/")
    console.print("[dim]Wait for 'Running on local URL' before opening the browser.[/dim]")
    launch_dashboard(host=host, port=port)


@app.command("kill-switch")
def kill_switch_cmd(
    off: bool = typer.Option(False, "--off", help="Remove kill file"),
) -> None:
    """Create or remove the KILL file to stop runs cooperatively."""

    layout = ensure_layout()
    k = layout["root"] / "KILL"
    if off and k.exists():
        k.unlink()
        console.print("Kill switch [green]OFF[/green]")
        return
    k.write_text("stop\n", encoding="utf-8")
    console.print(f"Kill switch [red]ON[/red] ({k})")


@app.command()
def version() -> None:
    console.print(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
