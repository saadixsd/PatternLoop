"""Trigger OSS n8n workflows via webhook with optional HMAC."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

import httpx


def sign_body(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def trigger_n8n_webhook(
    *,
    url: str,
    payload: dict[str, Any],
    secret_env: str,
    timeout: float = 60.0,
) -> dict[str, Any]:
    body = json.dumps(payload, default=str).encode()
    headers = {"content-type": "application/json"}
    secret = os.environ.get(secret_env, "")
    if secret:
        headers["x-patternloop-signature"] = sign_body(secret, body)
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, content=body, headers=headers)
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return {"raw": r.text}
