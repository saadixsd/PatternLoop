# Release checklist

- [ ] `ruff check src tests`
- [ ] `pytest`
- [ ] `patternloop --help` and `patternloop init`
- [ ] Smoke: `patternloop agents install research_digest --yes` with `--mock`
- [ ] Verify Gradio binds to `127.0.0.1` only
- [ ] Verify `docs/SECURITY.md` still matches connector flags
- [ ] Tag: `git tag v0.1.0`

## v0.1.0 scope

Core LoopSpec compiler, execution kernel (Ollama default), bundled starters, localhost UI, `.agent` import/export, optional Claude + n8n hooks.
