# PatternLoop — vision

## Problem

Powerful agent frameworks exist, but they are often framework-heavy, cloud-centric, or opaque. Many teams want a **local**, **auditable** loop: a pattern they own, that improves with use, without shipping data to a vendor.

## What PatternLoop is

1. **Pattern compiler** — Goals plus 2–5 example traces become a structured **LoopSpec** (prompts, tools, success checks, limits), versioned on disk.
2. **Execution kernel** — ReAct-style **plan → act → observe → score → adapt** with hard caps (steps, time, remote usage).
3. **Trust boundary** — Default **local-only**. Optional **Claude** or **n8n** connectors require explicit configuration and environment credentials.

PatternLoop is **not** “swap the model and rerun the same prompt.” The product is the **loop artifact** and the **kernel** that runs it safely.

## Non-goals (for the open core)

- Replacing LangGraph/CrewAI for every enterprise workflow.
- Hosted multi-tenant SaaS inside this repository.
- Sending user content to the cloud without an explicit, named connector.

## Comparison (honest)

| | PatternLoop | Typical agent framework |
|---|-------------|-------------------------|
| Primary artifact | LoopSpec on disk | Code + graph definitions |
| Default runtime | Ollama locally | Often cloud APIs |
| Learning | Compile examples → LoopSpec; adapt within bounds | Often static prompts or separate training |
| Safety posture | Allowlists, redacted logs, opt-in remote | Varies |

## One-liner

*Local agent OS: compile your workflow into a loop that improves until the goal predicate passes.*
