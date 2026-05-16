# Engineering journal

Short log of decisions and tradeoffs. Append newest entries at the top.

## 2026-05-15 — Initial implementation

- **License:** MIT for maximum adoption; AGPL noted in SECURITY docs as alternative for forks that need copyleft.
- **Layout:** `src/patternloop` setuptools package; data under `~/.patternloop` or `PATTERNLOOP_HOME`.
- **LoopSpec:** YAML on disk; compiler uses local Ollama (or mock) to draft turns from traces; user can edit before save.
- **Memory:** SQLite + JSON episodes for simplicity (Chroma optional later); no cloud vector DB in core.
- **UI:** Gradio bound to `127.0.0.1` by default.
- **Packaging:** bundled LoopSpecs ship as package data; list via `Traversable.iterdir()`, copy one file at a time with `as_file()` (avoid returning a temp path that is deleted after the context manager exits).
- **CLI:** Gradio imports only inside `patternloop ui` so lightweight commands stay fast.
