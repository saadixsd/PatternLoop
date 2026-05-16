"""Inference backends — Ollama default, mock for tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class InferenceBackend(ABC):
    @abstractmethod
    def generate(self, system: str, user: str, temperature: float = 0.3) -> str:
        raise NotImplementedError


class OllamaBackend(InferenceBackend):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, system: str, user: str, temperature: float = 0.3) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "prompt": user,
            "stream": False,
            "options": {"temperature": temperature},
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return str(data.get("response", ""))


class MockBackend(InferenceBackend):
    def __init__(self, replies: list[str] | None = None) -> None:
        self._replies = replies or []
        self._idx = 0

    def generate(self, system: str, user: str, temperature: float = 0.3) -> str:
        if self._idx < len(self._replies):
            out = self._replies[self._idx]
            self._idx += 1
            return out
        return "FINAL: mock completion"
