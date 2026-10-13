"""SQLite persistence — snapshot history + cache index.

Runs in a threadpool via `asyncio.to_thread` (aiosqlite for hot paths).
Schema is tiny: one table for daily snapshots, one for metadata.
"""
from __future__ import annotations

import contextlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    generated_at TEXT NOT NULL,
    price_close  REAL,
    ret_pct      REAL,
    taker_share  REAL,
    bias_score   INTEGER,
    bias_state   TEXT,
    winner       TEXT,
    bull_pts     INTEGER,
    bear_pts     INTEGER,
    errors       INTEGER DEFAULT 0,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts DESC);

CREATE TABLE IF NOT EXISTS cache_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    ts    REAL NOT NULL
);
"""


async def init_db() -> None:
    """Create tables if missing. Safe to call on every startup."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def save_snapshot(snap: dict[str, Any]) -> int:
    """Persist a full snapshot row. Returns the row id."""
    price = snap.get("price", {})
    bias = snap.get("bias", {})
    players = snap.get("players", {})
    payload = json.dumps(snap, default=str)
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            """INSERT INTO snapshots
               (ts, generated_at, price_close, ret_pct, taker_share,
                bias_score, bias_state, winner, bull_pts, bear_pts, errors, payload)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                time.time(),
                snap.get("generated_at", datetime.now(UTC).isoformat()),
                price.get("close"),
                price.get("ret_pct"),
                price.get("taker_share"),
                bias.get("score"),
                bias.get("state"),
                players.get("winner"),
                players.get("bull_pts"),
                players.get("bear_pts"),
                len(snap.get("errors", [])),
                payload,
            ),
        )
        await db.commit()
        row_id = cur.lastrowid or 0

    # opportunistically trim (every ~50 inserts)
    if row_id % 50 == 0:
        with contextlib.suppress(Exception):
            await trim_snapshots(keep=500)

    return row_id


async def latest_snapshot() -> dict[str, Any] | None:
    """Return the most recent stored snapshot, or None."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT payload FROM snapshots ORDER BY ts DESC LIMIT 1"
        )
        row = await cur.fetchone()
        if row is None:
            return None
        result: dict[str, Any] = json.loads(row["payload"])
        return result


async def snapshot_history(days: int = 90) -> list[dict[str, Any]]:
    """Return daily-bias history rows for the history table."""
    cutoff = time.time() - days * 86400
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT date(generated_at) AS d,
                      MAX(price_close) AS close,
                      MAX(ret_pct) AS ret_pct,
                      MAX(taker_share) AS taker,
                      MAX(bias_score) AS bias_score,
                      MAX(winner) AS winner,
                      MAX(ts) AS ts
               FROM snapshots
               WHERE ts > ?
               GROUP BY d
               ORDER BY d DESC""",
            (cutoff,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_meta(key: str) -> str | None:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT value FROM cache_meta WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_meta(key: str, value: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT INTO cache_meta (key, value, ts) VALUES (?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=excluded.ts""",
            (key, value, time.time()),
        )
        await db.commit()


async def snapshot_count() -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT COUNT(*) FROM snapshots")
        row = await cur.fetchone()
        return row[0] if row else 0


async def trim_snapshots(keep: int = 500) -> int:
    """Keep only the most recent `keep` snapshot rows. Returns rows deleted."""
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            """DELETE FROM snapshots
               WHERE id NOT IN (
                   SELECT id FROM snapshots ORDER BY ts DESC LIMIT ?
               )""",
            (keep,),
        )
        await db.commit()
        return cur.rowcount or 0
