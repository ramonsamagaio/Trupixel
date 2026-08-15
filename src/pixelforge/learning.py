from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from .models import ContributionEvent

SCHEMA = """
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

class LearningLedger:
    def __init__(self, path: str | Path = "pixelforge-learning.sqlite3"):
        self.path = str(path)
        self._init()

    def _db(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._db() as db:
            db.executescript(SCHEMA)

    def record(self, event: ContributionEvent) -> None:
        payload = event.model_dump_json()
        with self._db() as db:
            db.execute("INSERT INTO contribution_events(ts,job_id,event_type,engine_version,operation,payload) VALUES(?,?,?,?,?,?)", (time.time(), event.job_id, event.event_type, event.engine_version, event.operation, payload))
            for rid in event.recipe_ids:
                db.execute("INSERT OR IGNORE INTO recipe_stats(recipe_id) VALUES(?)", (rid,))
                db.execute("UPDATE recipe_stats SET uses=uses+1 WHERE recipe_id=?", (rid,))
                if event.outcome == "accepted": db.execute("UPDATE recipe_stats SET accepted=accepted+1 WHERE recipe_id=?", (rid,))
                elif event.outcome == "rejected": db.execute("UPDATE recipe_stats SET rejected=rejected+1 WHERE recipe_id=?", (rid,))
                elif event.outcome == "reverted": db.execute("UPDATE recipe_stats SET reverted=reverted+1 WHERE recipe_id=?", (rid,))
                db.execute("UPDATE recipe_stats SET score=(accepted + 0.15) / (accepted + rejected + reverted*1.5 + 1.0) WHERE recipe_id=?", (rid,))

    def recipe_stats(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT recipe_id,uses,accepted,rejected,reverted,score FROM recipe_stats ORDER BY score DESC, uses DESC").fetchall()
        return [dict(recipe_id=r[0], uses=r[1], accepted=r[2], rejected=r[3], reverted=r[4], score=r[5]) for r in rows]
