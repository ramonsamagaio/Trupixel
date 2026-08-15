from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from .models import ContributionEvent

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS contribution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recipe_stats (
    recipe_id TEXT PRIMARY KEY,
    uses INTEGER NOT NULL DEFAULT 0,
    accepted REAL NOT NULL DEFAULT 0,
    rejected REAL NOT NULL DEFAULT 0,
    reverted REAL NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0
);
"""

POSTGRES_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS contribution_events (
        id BIGSERIAL PRIMARY KEY,
        ts DOUBLE PRECISION NOT NULL,
        job_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        engine_version TEXT NOT NULL,
        operation TEXT NOT NULL,
        payload TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipe_stats (
        recipe_id TEXT PRIMARY KEY,
        uses BIGINT NOT NULL DEFAULT 0,
        accepted DOUBLE PRECISION NOT NULL DEFAULT 0,
        rejected DOUBLE PRECISION NOT NULL DEFAULT 0,
        reverted DOUBLE PRECISION NOT NULL DEFAULT 0,
        score DOUBLE PRECISION NOT NULL DEFAULT 0
    )
    """,
)

DATABASE_ENV_KEYS = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_PRISMA_URL",
    "NEON_DATABASE_URL",
)


def _database_url() -> str | None:
    for key in DATABASE_ENV_KEYS:
        value = os.getenv(key)
        if value:
            return value
    return None


class LearningLedger:
    """Persistent learning ledger: Neon/Postgres when hosted, SQLite locally."""

    def __init__(self, path: str | Path = "trupixel-learning.sqlite3", database_url: str | None = None):
        self.path = str(path)
        self.database_url = database_url or _database_url()
        self.backend = "postgres" if self.database_url else "sqlite"
        self._init()

    def _sqlite(self):
        return sqlite3.connect(self.path)

    def _postgres(self):
        import psycopg
        assert self.database_url
        return psycopg.connect(self.database_url, connect_timeout=8)

    def _init(self) -> None:
        if self.backend == "postgres":
            with self._postgres() as db:
                with db.cursor() as cur:
                    for statement in POSTGRES_SCHEMA:
                        cur.execute(statement)
            return
        with self._sqlite() as db:
            db.executescript(SQLITE_SCHEMA)

    def record(self, event: ContributionEvent) -> None:
        if self.backend == "postgres":
            self._record_postgres(event)
        else:
            self._record_sqlite(event)

    def _record_postgres(self, event: ContributionEvent) -> None:
        payload = event.model_dump_json()
        with self._postgres() as db:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO contribution_events (ts,job_id,event_type,engine_version,operation,payload) VALUES (%s,%s,%s,%s,%s,%s)",
                    (time.time(), event.job_id, event.event_type, event.engine_version, event.operation, payload),
                )
                for rid in event.recipe_ids:
                    cur.execute("INSERT INTO recipe_stats(recipe_id) VALUES (%s) ON CONFLICT (recipe_id) DO NOTHING", (rid,))
                    cur.execute("UPDATE recipe_stats SET uses=uses+1 WHERE recipe_id=%s", (rid,))
                    if event.outcome == "accepted":
                        cur.execute("UPDATE recipe_stats SET accepted=accepted+1 WHERE recipe_id=%s", (rid,))
                    elif event.outcome == "rejected":
                        cur.execute("UPDATE recipe_stats SET rejected=rejected+1 WHERE recipe_id=%s", (rid,))
                    elif event.outcome == "reverted":
                        cur.execute("UPDATE recipe_stats SET reverted=reverted+1 WHERE recipe_id=%s", (rid,))
                    cur.execute(
                        "UPDATE recipe_stats SET score=(accepted + 0.15) / (accepted + rejected + reverted*1.5 + 1.0) WHERE recipe_id=%s",
                        (rid,),
                    )

    def _record_sqlite(self, event: ContributionEvent) -> None:
        payload = event.model_dump_json()
        with self._sqlite() as db:
            db.execute(
                "INSERT INTO contribution_events(ts,job_id,event_type,engine_version,operation,payload) VALUES(?,?,?,?,?,?)",
                (time.time(), event.job_id, event.event_type, event.engine_version, event.operation, payload),
            )
            for rid in event.recipe_ids:
                db.execute("INSERT OR IGNORE INTO recipe_stats(recipe_id) VALUES(?)", (rid,))
                db.execute("UPDATE recipe_stats SET uses=uses+1 WHERE recipe_id=?", (rid,))
                if event.outcome == "accepted":
                    db.execute("UPDATE recipe_stats SET accepted=accepted+1 WHERE recipe_id=?", (rid,))
                elif event.outcome == "rejected":
                    db.execute("UPDATE recipe_stats SET rejected=rejected+1 WHERE recipe_id=?", (rid,))
                elif event.outcome == "reverted":
                    db.execute("UPDATE recipe_stats SET reverted=reverted+1 WHERE recipe_id=?", (rid,))
                db.execute(
                    "UPDATE recipe_stats SET score=(accepted + 0.15) / (accepted + rejected + reverted*1.5 + 1.0) WHERE recipe_id=?",
                    (rid,),
                )

    def recipe_stats(self) -> list[dict]:
        query = "SELECT recipe_id,uses,accepted,rejected,reverted,score FROM recipe_stats ORDER BY score DESC, uses DESC"
        if self.backend == "postgres":
            with self._postgres() as db:
                with db.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall()
        else:
            with self._sqlite() as db:
                rows = db.execute(query).fetchall()
        return [
            dict(recipe_id=r[0], uses=r[1], accepted=r[2], rejected=r[3], reverted=r[4], score=r[5])
            for r in rows
        ]
