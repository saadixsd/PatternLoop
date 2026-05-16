from pathlib import Path

from patternloop.tools.registry import parse_tool_call_json
from patternloop.tools.sandbox import FileSandbox


def test_parse_tool_call_strips_markdown_bold() -> None:
    text = """
Intro blah

**TOOL_CALL:** {"name": "list_dir", "arguments": {"path": "."}}
"""
    name, args = parse_tool_call_json(text)
    assert name == "list_dir"
    assert args == {"path": "."}


def test_sandbox_read(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    fs = FileSandbox([root])
    res = fs.read_file("a.txt")
    assert res.ok
    assert "hello" in res.data.get("content", "")


def test_sandbox_denies_escape(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    fs = FileSandbox([root])
    outside = tmp_path / "secret.txt"
    outside.write_text("no")
    res = fs.read_file(str(outside))
    assert not res.ok
