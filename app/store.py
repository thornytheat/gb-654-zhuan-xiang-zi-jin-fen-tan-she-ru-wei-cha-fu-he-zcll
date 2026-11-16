from __future__ import annotations
import json
from pathlib import Path
import sqlite3

class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (digest TEXT PRIMARY KEY, run_id TEXT NOT NULL, result TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path)

    def record(self, digest: str, run_id: str, result: dict) -> dict:
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO runs VALUES (?, ?, ?)",
                       (digest, run_id, json.dumps(result, ensure_ascii=False, sort_keys=True)))
            row = db.execute("SELECT run_id, result FROM runs WHERE digest=?", (digest,)).fetchone()
        return {"run_id": row[0], "result": json.loads(row[1])}

    def count(self) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]

    def all(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT run_id, digest, result FROM runs ORDER BY run_id").fetchall()
        return [{"run_id": r[0], "digest": r[1], "result": json.loads(r[2])} for r in rows]
