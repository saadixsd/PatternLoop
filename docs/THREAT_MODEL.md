# Threat model (abbreviated)

## Assets

- User files inside allowlisted paths.
- LoopSpecs, run transcripts, episodic SQLite DB under the data directory.
- Optional API keys in environment for connectors.

## Adversaries

- **Malicious prompt / tool injection** via model output directing unexpected tool args.
- **Over-broad read roots** misconfigured by user.
- **Supply chain**: malicious `.agent` bundles importing unexpected YAML (mitigated by user review before `import-bundle`).

## Controls

- Hard caps on iterations, tool calls, wall time.
- Cooperative **kill switch** file (`KILL` in data root).
- Redacted logging; no secrets in LoopSpec schema.
- Read-only sandbox by default.

## Out of scope (MVP)

- Full syscall sandboxing or container isolation (future hardening).
- Enterprise SSO / RBAC.
