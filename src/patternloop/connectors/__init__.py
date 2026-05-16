"""Connectors package — opt-in Claude / n8n."""

from patternloop.connectors.claude import ClaudeBackend
from patternloop.connectors.n8n import trigger_n8n_webhook

__all__ = ["ClaudeBackend", "trigger_n8n_webhook"]
