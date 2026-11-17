from decimal import Decimal, ROUND_DOWN

SAMPLE = {"total": "10.00", "shares": {"A": "0.333", "B": "0.333", "C": "0.334"}}
SETTLE_SAMPLE = {
    "pool_id": "pool-2026-11",
    "total": "100.01",
    "items": [
        {"id": "A", "weight": "1", "cap": "40.00"},
        {"id": "B", "weight": "1", "cap": "40.00"},
        {"id": "C", "weight": "1", "cap": "40.00"},
    ],
}
QUANTUM = Decimal("0.01")


def largest_remainder(total, shares, quantum=QUANTUM, owed=None):
    """最大余额法把总额落到最小单位。

    尾差相同若总按项目编号补分，同一项目会反复获益；传入欠分表后，
    尾差相同改按累计欠分（欠多者优先），项目编号仅作稳定兜底。
    """
    total = Decimal(str(total))
    quantum = Decimal(str(quantum))
    raw = {str(k): total * Decimal(str(v)) for k, v in shares.items()}
    base = {k: v.quantize(quantum, rounding=ROUND_DOWN) for k, v in raw.items()}
    units = int(((total - sum(base.values())) / quantum).to_integral_value())
    if owed is None:
        order = sorted(raw, key=lambda k: (-(raw[k] - base[k]), k))
    else:
        order = sorted(raw, key=lambda k: (-(raw[k] - base[k]), -Decimal(str(owed.get(k, 0))), k))
    for key in order[:units]:
        base[key] += quantum
    return base


def plan_settlement(total, items, owed=None, quantum=QUANTUM):
    """按资金池生成一批尾差裁决计划（纯函数，不写库）。

    排序键：尾差降序 → 累计欠分降序 → 项目编号。补分逐个最小单位进行，
    触及封顶的项目跳过；发不出去的单位计为未分配款保留，
    不改资格与预算采信输入。
    """
    quantum = Decimal(str(quantum))
    total = Decimal(str(total))
    owed = {str(k): Decimal(str(v)) for k, v in (owed or {}).items()}
    entries = []
    seen = set()
    for item in items:
        pid = str(item["id"])
        if pid in seen:
            raise ValueError("DUPLICATE_CONFLICT")
        seen.add(pid)
        entry = {"id": pid, "weight": Decimal(str(item["weight"])), "cap": Decimal(str(item["cap"]))}
        if entry["weight"] < 0:
            raise ValueError("NEGATIVE_WEIGHT")
        if entry["cap"] < 0:
            raise ValueError("INVALID_VALUE")
        entries.append(entry)
    if not entries:
        raise ValueError("EMPTY_VALUE")
    if total < 0:
        raise ValueError("INVALID_VALUE")
    total_weight = sum((e["weight"] for e in entries), Decimal(0))
    if total_weight <= 0:
        raise ValueError("ZERO_WEIGHT_GROUP")
    raw = {e["id"]: total * e["weight"] / total_weight for e in entries}
    base = {k: v.quantize(quantum, rounding=ROUND_DOWN) for k, v in raw.items()}
    units = int(((total - sum(base.values())) / quantum).to_integral_value())
    order = sorted(raw, key=lambda k: (-(raw[k] - base[k]), -owed.get(k, Decimal(0)), k))
    caps = {e["id"]: e["cap"] for e in entries}
    grants = {k: Decimal(0) for k in raw}
    rationale = []
    for rank, pid in enumerate(order, 1):
        rationale.append({
            "project_id": pid, "rank": rank, "raw": raw[pid], "base": base[pid],
            "frac": raw[pid] - base[pid], "owed_before": owed.get(pid, Decimal(0)),
            "cap": caps[pid], "room": caps[pid] - base[pid], "grant": Decimal(0), "note": "OUT_OF_UNITS",
        })
    for r in rationale:
        if units <= 0:
            break
        if r["room"] >= quantum:
            r["grant"] = grants[r["project_id"]] = quantum
            units -= 1
            r["note"] = "GRANTED"
        else:
            r["note"] = "CAP_FULL"
    amounts = {k: base[k] + grants[k] for k in raw}
    return {
        "amounts": amounts, "grants": grants,
        "unallocated": total - sum(amounts.values(), Decimal(0)),
        "rationale": rationale, "quantum": quantum,
    }


def apply_to_owed(owed, plan):
    """按裁决计划滚动欠分账本（纯函数）。

    参与者：欠分 += 本批尾差 - 实补；未参与者：保留欠分、本批不补。
    守恒：欠分总增量 == 未分配款，历史误差由后续批次补偿承接，
    已结批次不回改。
    """
    new_owed = {str(k): Decimal(str(v)) for k, v in (owed or {}).items()}
    for r in plan["rationale"]:
        pid = r["project_id"]
        new_owed[pid] = new_owed.get(pid, Decimal(0)) + r["frac"] - r["grant"]
    return new_owed


def settle_payload(payload, owed):
    """用冻结输入快照与欠分账本生成完整裁决结果（纯函数，可复算）。"""
    owed = {str(k): Decimal(str(v)) for k, v in (owed or {}).items()}
    plan = plan_settlement(payload["total"], payload["items"], owed)
    owed_after = apply_to_owed(owed, plan)
    amounts = plan["amounts"]
    return {
        "pool_id": payload["pool_id"],
        "batch_id": payload["batch_id"],
        "expected_version": int(payload["expected_version"]),
        "quantum": str(plan["quantum"]),
        "input_count": len(payload["items"]),
        "valid_count": len(payload["items"]),
        "quarantine_count": 0,
        "amounts": {k: str(v) for k, v in amounts.items()},
        "grants": {k: str(v) for k, v in plan["grants"].items()},
        "allocated_total": str(sum(amounts.values(), Decimal(0))),
        "unallocated": str(plan["unallocated"]),
        "owed_before": {k: str(v) for k, v in owed.items()},
        "owed_after": {k: str(v) for k, v in owed_after.items()},
        "rationale": [
            {
                "project_id": r["project_id"], "rank": r["rank"], "raw": str(r["raw"]),
                "base": str(r["base"]), "frac": str(r["frac"]), "owed_before": str(r["owed_before"]),
                "cap": str(r["cap"]), "room": str(r["room"]), "grant": str(r["grant"]), "note": r["note"],
            }
            for r in plan["rationale"]
        ],
        "reason": "OK" if plan["unallocated"] == 0 else "CAP_LIMIT",
    }


def run(payload):
    d = SAMPLE | payload
    out = largest_remainder(d["total"], d["shares"])
    return {"status": "READY", "input_count": len(out), "valid_count": len(out), "quarantine_count": 0,
            "amounts": {k: str(v) for k, v in out.items()}, "total": str(sum(out.values())), "reason": "OK"}
