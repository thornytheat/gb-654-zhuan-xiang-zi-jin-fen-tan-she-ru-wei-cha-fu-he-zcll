from __future__ import annotations
from decimal import Decimal, InvalidOperation

from app.errors import DomainError
from app.manifest import canonical_digest
from . import core


def execute(payload: dict | None = None) -> dict:
    return core.run(payload or core.SAMPLE)


def _normalize(payload: dict | None) -> tuple[str, str, int | None, dict]:
    data = core.SETTLE_SAMPLE | dict(payload or {})
    pool_id = str(data["pool_id"])
    items = []
    for item in data["items"]:
        try:
            items.append({"id": str(item["id"]), "weight": str(item["weight"]), "cap": str(item["cap"])})
        except (KeyError, TypeError) as exc:
            raise DomainError("INVALID_VALUE", f"结批项目缺少字段：{exc}")
    total = str(data["total"])
    raw_version = data.get("expected_version")
    try:
        expected_version = None if raw_version in (None, "") else int(raw_version)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", "expected_version 必须为整数")
    snapshot = {"pool_id": pool_id, "total": total, "items": items, "expected_version": expected_version}
    batch_id = str(data.get("batch_id") or "").strip() or "batch-" + canonical_digest(snapshot)[:12]
    snapshot["batch_id"] = batch_id
    return pool_id, batch_id, expected_version, snapshot


def settle(store, payload: dict | None = None) -> dict:
    """按资金池结批：版本校验、欠分滚动、幂等回放都在 Store 事务内完成。"""
    pool_id, batch_id, expected_version, snapshot = _normalize(payload)
    try:
        core.plan_settlement(snapshot["total"], snapshot["items"], {})  # 预校验，非法输入不落批次
    except InvalidOperation:
        raise DomainError("INVALID_VALUE", "金额或权重无法解析为数值")
    except ValueError as exc:
        raise DomainError(str(exc), str(exc))
    out = store.settle(pool_id, batch_id, expected_version, snapshot, core.settle_payload)
    return {"status": "READY", "idempotent_replay": out["replay"], **out["result"]}


def pools_view(store) -> list[dict]:
    return store.pools()


def ledger_view(store, pool_id: str | None = None) -> list[dict]:
    return store.ledger(pool_id)


def batches_view(store, pool_id: str | None = None) -> list[dict]:
    out = []
    for batch in store.batches(pool_id):
        result = batch["result"] or {}
        out.append({
            "batch_id": batch["batch_id"], "pool_id": batch["pool_id"], "status": batch["status"],
            "expected_version": batch["expected_version"], "version": result.get("version"),
            "allocated_total": result.get("allocated_total"), "unallocated": result.get("unallocated"),
            "reason": result.get("reason"), "rationale": result.get("rationale", []),
        })
    return out


def batch_view(store, batch_id: str) -> dict:
    batch = store.batch(batch_id)
    if batch is None:
        raise DomainError("BATCH_NOT_FOUND", f"批次 {batch_id} 不存在")
    return batch


def verify(store, batch_id: str) -> dict:
    """已结批次按当时依据复算：冻结快照 + 当时欠分重算，只比对、不回改。"""
    batch = batch_view(store, batch_id)
    if batch["status"] != "SETTLED":
        raise DomainError("BATCH_NOT_SETTLED", f"批次 {batch_id} 状态为 {batch['status']}，仅已结批次可复算")
    frozen = batch["result"]
    owed_before = {pid: Decimal(text) for pid, text in frozen["owed_before"].items()}
    recomputed = core.settle_payload(batch["payload"], owed_before)
    keys = ("amounts", "grants", "allocated_total", "unallocated", "owed_after")
    diff = {key: {"frozen": frozen.get(key), "recomputed": recomputed.get(key)}
            for key in keys if frozen.get(key) != recomputed.get(key)}
    return {"batch_id": batch_id, "consistent": not diff, "diff": diff,
            "basis": "冻结输入快照与当时欠分复算，已结批次不回改"}


def recover(store) -> list[dict]:
    return store.recover(core.settle_payload)
