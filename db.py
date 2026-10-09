"""SQLite scan history (stretch feature)."""
from __future__ import annotations

import sqlite3
import time

DB_FILE = "bantay_boses.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_FILE)
    c.execute(
        """CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            kind TEXT NOT NULL,
            level TEXT NOT NULL,
            score INTEGER NOT NULL,
            text TEXT NOT NULL
        )"""
    )
    return c


def save(kind: str, level: str, score: int, text: str) -> None:
    try:
        with _conn() as c:
            c.execute("INSERT INTO scans (ts, kind, level, score, text) VALUES (?,?,?,?,?)",
                      (time.time(), kind, level, score, text[:2000]))
    except Exception:
        pass


def history(limit: int = 50) -> list[dict]:
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT ts, kind, level, score, text FROM scans "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"ts": r[0], "kind": r[1], "level": r[2], "score": r[3], "text": r[4]}
                for r in rows]
    except Exception:
        return []
