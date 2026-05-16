# Security

## Local-first defaults

- Data directory default: `~/.patternloop` (override with `PATTERNLOOP_HOME` or `XDG_DATA_HOME/patternloop`).
- LoopSpecs and run logs stay on your machine unless you explicitly export a `.agent` bundle.

## Credentials

- Do not put API keys inside LoopSpec YAML. Connectors read **environment variables** (e.g. `ANTHROPIC_API_KEY`, `PATTERNLOOP_N8N_HMAC_SECRET`).
- Logs apply **redaction** for common secret patterns. Treat logs as sensitive anyway.

## Remote connectors

- **Claude** and **n8n** are **disabled by default**. Enabling them requires editing `config.yaml` under your data root.
- n8n webhooks can include an HMAC header when a secret is set.

## Tooling

- Filesystem tools are restricted to **allowlisted roots** (CLI `--workdir`).
- Bash / writes are **off** unless explicitly enabled in config.

## Telemetry

- None by default in this repository build.

## Reporting

- Open an issue for suspected vulnerabilities; avoid posting reproduction traces that contain secrets.
