"""Lightweight SQLite episodic memory for runs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class EpisodicMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT NOT NULL,
              step TEXT NOT NULL,
              payload TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def append(self, run_id: str, step: str, payload: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO episodes (run_id, step, payload) VALUES (?, ?, ?)",
            (run_id, step, json.dumps(payload, default=str)),
        )
        self._conn.commit()

    def recent_for_pattern(self, pattern_name: str, limit: int = 20) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT run_id, step, payload FROM episodes
            WHERE payload LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (f'%\"pattern\": "{pattern_name}"%', limit),
        )
        rows = []
        for run_id, step, payload in cur.fetchall():
            try:
                rows.append({"run_id": run_id, "step": step, "payload": json.loads(payload)})
            except json.JSONDecodeError:
                continue
        return rows

    def close(self) -> None:
        self._conn.close()
