"""Structured logging with redaction of common secret patterns."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-ant-api\S+", re.I), "[REDACTED_ANT]"),
    (re.compile(r"sk_live\S+", re.I), "[REDACTED_STRIPE]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+/]+=*", re.I), "Bearer [REDACTED]"),
    (re.compile(r"x-api-key:\s*\S+", re.I), "x-api-key: [REDACTED]"),
    (re.compile(r"['\"]?api_key['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.I), 'api_key: "[REDACTED]"'),
]


def redact_text(text: str) -> str:
    out = text
    for pat, repl in _SECRET_PATTERNS:
        out = pat.sub(repl, out)
    return out


def redact_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def safe_json(obj: Any) -> str:
    try:
        return json.dumps(redact_obj(obj), default=str, ensure_ascii=False)[:50000]
    except Exception:
        return redact_text(str(obj))[:50000]
