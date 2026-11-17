from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from decimal import Decimal

from .errors import DomainError

class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (digest TEXT PRIMARY KEY, run_id TEXT NOT NULL, result TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS remainder_pools (pool_id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 0)")
            db.execute("CREATE TABLE IF NOT EXISTS remainder_ledger (pool_id TEXT NOT NULL, project_id TEXT NOT NULL, owed TEXT NOT NULL, PRIMARY KEY (pool_id, project_id))")
            db.execute("CREATE TABLE IF NOT EXISTS remainder_batches (batch_id TEXT PRIMARY KEY, pool_id TEXT NOT NULL, status TEXT NOT NULL, expected_version INTEGER NOT NULL, payload TEXT NOT NULL, result TEXT)")

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

    # ---- M5 尾差裁决：资金池欠分账本与结批 ----

    def _pool_version(self, db, pool_id: str) -> int:
        row = db.execute("SELECT version FROM remainder_pools WHERE pool_id=?", (pool_id,)).fetchone()
        return row[0] if row else 0

    def pool_version(self, pool_id: str) -> int:
        with self.connect() as db:
            return self._pool_version(db, pool_id)

    def pools(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT pool_id, version FROM remainder_pools ORDER BY pool_id").fetchall()
        return [{"pool_id": r[0], "version": r[1]} for r in rows]

    def ledger(self, pool_id: str | None = None) -> list[dict]:
        sql = "SELECT pool_id, project_id, owed FROM remainder_ledger"
        args: tuple = ()
        if pool_id is not None:
            sql += " WHERE pool_id=?"
            args = (pool_id,)
        sql += " ORDER BY pool_id, project_id"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [{"pool_id": r[0], "project_id": r[1], "owed": r[2]} for r in rows]

    def batches(self, pool_id: str | None = None) -> list[dict]:
        sql = "SELECT batch_id, pool_id, status, expected_version, payload, result FROM remainder_batches"
        args: tuple = ()
        if pool_id is not None:
            sql += " WHERE pool_id=?"
            args = (pool_id,)
        sql += " ORDER BY rowid"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [self._batch_row(r) for r in rows]

    def batch(self, batch_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT batch_id, pool_id, status, expected_version, payload, result FROM remainder_batches WHERE batch_id=?",
                             (batch_id,)).fetchone()
        return self._batch_row(row) if row else None

    @staticmethod
    def _batch_row(row) -> dict:
        return {"batch_id": row[0], "pool_id": row[1], "status": row[2], "expected_version": row[3],
                "payload": json.loads(row[4]), "result": json.loads(row[5]) if row[5] else None}

    def settle(self, pool_id: str, batch_id: str, expected_version: int | None, payload: dict, compute) -> dict:
        """登记并完成一次结批；compute(冻结快照, 当前欠分) -> 裁决结果。

        两阶段：先登记 SETTLING（中断可恢复），再在 IMMEDIATE 事务内复核版本、
        滚动欠分、推进池版本并落 SETTLED。同 batch_id 重试幂等回放，不重复扣补；
        并发结批在版本复核处拒绝过期版本。
        """
        with self.connect() as db:
            row = db.execute("SELECT status, result FROM remainder_batches WHERE batch_id=?", (batch_id,)).fetchone()
            if row and row[0] == "SETTLED":
                return {"result": json.loads(row[1]), "replay": True}
            if row and row[0] == "STALE":
                raise DomainError("STALE_VERSION", f"批次 {batch_id} 已因版本过期被拒绝，请刷新版本后更换批次编号重试")
            if row is None:
                current = self._pool_version(db, pool_id)
                if expected_version is None:
                    expected_version = current
                if current != expected_version:
                    raise DomainError("STALE_VERSION", f"资金池 {pool_id} 当前账本版本 {current}，与提交版本 {expected_version} 不符")
                snapshot = json.dumps({**payload, "expected_version": expected_version}, ensure_ascii=False, sort_keys=True)
                db.execute("INSERT INTO remainder_batches (batch_id, pool_id, status, expected_version, payload) VALUES (?,?,?,?,?)",
                           (batch_id, pool_id, "SETTLING", expected_version, snapshot))
        return self._finish(batch_id, compute)

    def _finish(self, batch_id: str, compute) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT pool_id, status, expected_version, payload, result FROM remainder_batches WHERE batch_id=?",
                             (batch_id,)).fetchone()
            if row is None:
                db.rollback()
                raise DomainError("BATCH_NOT_FOUND", f"批次 {batch_id} 不存在")
            pool_id, status, expected_version, payload_raw, result_raw = row
            if status == "SETTLED":
                db.commit()
                return {"result": json.loads(result_raw), "replay": True}
            current = self._pool_version(db, pool_id)
            if current != expected_version:
                db.execute("UPDATE remainder_batches SET status='STALE' WHERE batch_id=?", (batch_id,))
                db.commit()
                raise DomainError("STALE_VERSION",
                                  f"资金池 {pool_id} 账本版本已推进到 {current}，批次 {batch_id} 按过期版本 {expected_version} 结批被拒绝")
            owed = {pid: Decimal(text) for pid, text in
                    db.execute("SELECT project_id, owed FROM remainder_ledger WHERE pool_id=?", (pool_id,)).fetchall()}
            result = compute(json.loads(payload_raw), owed)
            result["version"] = current + 1
            for pid, text in result["owed_after"].items():
                db.execute("INSERT INTO remainder_ledger (pool_id, project_id, owed) VALUES (?,?,?) "
                           "ON CONFLICT(pool_id, project_id) DO UPDATE SET owed=excluded.owed",
                           (pool_id, pid, str(text)))
            db.execute("INSERT INTO remainder_pools (pool_id, version) VALUES (?,?) "
                       "ON CONFLICT(pool_id) DO UPDATE SET version=excluded.version", (pool_id, current + 1))
            db.execute("UPDATE remainder_batches SET status='SETTLED', result=? WHERE batch_id=?",
                       (json.dumps(result, ensure_ascii=False, sort_keys=True), batch_id))
            db.commit()
        return {"result": result, "replay": False}

    def recover(self, compute) -> list[dict]:
        """恢复中断的未完裁决：重放 SETTLING 批次；版本已过期的标记 STALE，不扣账。"""
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT batch_id FROM remainder_batches WHERE status='SETTLING' ORDER BY rowid").fetchall()]
        out = []
        for batch_id in ids:
            try:
                finished = self._finish(batch_id, compute)
                out.append({"batch_id": batch_id, "status": "SETTLED", "replay": finished["replay"]})
            except DomainError as exc:
                out.append({"batch_id": batch_id, "status": exc.code})
            except ValueError as exc:
                out.append({"batch_id": batch_id, "status": str(exc) or "INVALID_VALUE"})
        return out
