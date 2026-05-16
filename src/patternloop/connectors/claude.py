"""Optional Anthropic Claude backend (user API key, opt-in)."""

from __future__ import annotations

import os

import httpx

from patternloop.inference import InferenceBackend


class ClaudeBackend(InferenceBackend):
    def __init__(
        self,
        *,
        model: str,
        max_tokens: int = 4096,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("Claude backend requires ANTHROPIC_API_KEY")

    def generate(self, system: str, user: str, temperature: float = 0.3) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            blocks = data.get("content") or []
            parts: list[str] = []
            for b in blocks:
                if b.get("type") == "text":
                    parts.append(str(b.get("text", "")))
            return "\n".join(parts)
