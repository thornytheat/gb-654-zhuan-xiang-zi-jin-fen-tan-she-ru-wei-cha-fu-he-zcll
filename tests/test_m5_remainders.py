import json
from decimal import Decimal

import pytest

from app.errors import DomainError
from app.modules.m5_remainders import service
from app.modules.m5_remainders.core import apply_to_owed, largest_remainder, plan_settlement, run
from app.store import Store


def test_trap_1(): # TRAP-10
    assert sum(largest_remainder("10.00",{"A":"0.333","B":"0.333","C":"0.334"}).values())==Decimal("10.00")
def test_trap_2():
    assert largest_remainder("0.01",{"A":"0.5","B":"0.5"})=={"A":Decimal("0.01"),"B":Decimal("0.00")}
def test_largest_gets_cent(): assert largest_remainder("1.00",{"A":"0.334","B":"0.333","C":"0.333"})["A"]==Decimal("0.34")
def test_quantized(): assert all(x.as_tuple().exponent==-2 for x in largest_remainder("1.00",{"A":"1"}).values())
def test_single(): assert largest_remainder("2.00",{"A":"1"})["A"]==Decimal("2.00")
def test_order_independent(): assert largest_remainder("1.00",{"B":"0.5","A":"0.5"})==largest_remainder("1.00",{"A":"0.5","B":"0.5"})
def test_run_total(): assert run({})["total"]=="10.00"
def test_run_count(): assert run({})["valid_count"]==3


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "m5.db"))


def settle(store, **over):
    payload = {"pool_id": "P", "total": "0.01",
               "items": [{"id": "A", "weight": "1", "cap": "10"}, {"id": "B", "weight": "1", "cap": "10"}]}
    payload.update(over)
    return service.settle(store, payload)


def insert_settling(store, batch_id, expected_version, pool_id="P"):
    payload = {"pool_id": pool_id, "batch_id": batch_id, "total": "0.01",
               "items": [{"id": "A", "weight": "1", "cap": "10"}, {"id": "B", "weight": "1", "cap": "10"}],
               "expected_version": expected_version}
    with store.connect() as db:
        db.execute("INSERT INTO remainder_batches (batch_id, pool_id, status, expected_version, payload) VALUES (?,?,?,?,?)",
                   (batch_id, pool_id, "SETTLING", expected_version, json.dumps(payload, ensure_ascii=False, sort_keys=True)))


# ---- 轮补反映累计欠分 ----

def test_tie_break_by_owed():
    out = largest_remainder("0.01", {"A": "0.5", "B": "0.5"}, owed={"A": "0", "B": "0.004"})
    assert out == {"A": Decimal("0.00"), "B": Decimal("0.01")}


def test_rotation_across_batches(store):
    first = settle(store)
    assert first["grants"] == {"A": "0.01", "B": "0"}
    second = settle(store, expected_version=1)
    assert second["grants"] == {"A": "0", "B": "0.01"}  # 欠分多者优先，不再固定同一项目
    third = settle(store, expected_version=2)
    assert third["grants"] == {"A": "0.01", "B": "0"}


def test_owed_rolls_with_grant(store):
    first = settle(store)
    assert first["owed_after"] == {"A": "-0.005", "B": "0.005"}
    second = settle(store, expected_version=1)
    assert {k: Decimal(v) for k, v in second["owed_after"].items()} == {"A": Decimal(0), "B": Decimal(0)}


# ---- 总额与封顶 ----

def test_cap_keeps_unallocated(store):
    out = settle(store, total="0.05",
                 items=[{"id": "A", "weight": "1", "cap": "0.02"}, {"id": "B", "weight": "1", "cap": "0.02"}])
    assert out["reason"] == "CAP_LIMIT"
    assert out["unallocated"] == "0.01"
    assert Decimal(out["allocated_total"]) + Decimal(out["unallocated"]) == Decimal("0.05")
    assert out["amounts"] == {"A": "0.02", "B": "0.02"}


def test_owed_conservation_equals_unallocated(store):
    out = settle(store, total="0.05",
                 items=[{"id": "A", "weight": "1", "cap": "0.02"}, {"id": "B", "weight": "1", "cap": "0.02"}])
    gain = sum(Decimal(v) for v in out["owed_after"].values()) - sum(Decimal(v) for v in out["owed_before"].values())
    assert gain == Decimal(out["unallocated"])  # 历史误差由后续补偿承接


def test_frozen_inputs_not_rewritten(store):
    out = settle(store, total="0.05",
                 items=[{"id": "A", "weight": "1", "cap": "0.02"}, {"id": "B", "weight": "1", "cap": "0.02"}])
    caps = {i["id"]: i["cap"] for i in store.batch(out["batch_id"])["payload"]["items"]}
    assert caps == {"A": "0.02", "B": "0.02"}  # 不改预算采信输入


def test_plan_respects_total_and_cap():
    plan = plan_settlement("0.05", [{"id": "A", "weight": "1", "cap": "0.02"}, {"id": "B", "weight": "1", "cap": "0.02"}])
    assert sum(plan["amounts"].values()) + plan["unallocated"] == Decimal("0.05")
    assert all(v <= Decimal("0.02") for v in plan["amounts"].values())


# ---- 资金池隔离与未参与项目 ----

def test_pool_isolation(store):
    settle(store, pool_id="P1", batch_id="p1-b1")
    settle(store, pool_id="P2", batch_id="p2-b1")
    assert store.pool_version("P1") == store.pool_version("P2") == 1
    p2_before = {r["project_id"]: r["owed"] for r in store.ledger("P2")}
    settle(store, pool_id="P1", batch_id="p1-b2", expected_version=1)
    assert store.pool_version("P1") == 2 and store.pool_version("P2") == 1
    assert {r["project_id"]: r["owed"] for r in store.ledger("P2")} == p2_before


def test_absent_project_keeps_owed_without_grant(store):
    settle(store)  # A 补 0.01，B 欠 0.005
    out = settle(store, expected_version=1,
                 items=[{"id": "A", "weight": "1", "cap": "10"}, {"id": "C", "weight": "1", "cap": "10"}])
    assert "B" not in out["grants"]            # 未参与不获本批补分
    assert out["owed_after"]["B"] == "0.005"   # 欠分保留
    assert out["grants"] == {"A": "0", "C": "0.01"}


def test_apply_to_owed_skips_absent():
    plan = plan_settlement("0.01", [{"id": "A", "weight": "1", "cap": "10"}, {"id": "B", "weight": "1", "cap": "10"}],
                           owed={"Z": "0.003"})
    assert apply_to_owed({"Z": "0.003"}, plan)["Z"] == Decimal("0.003")


# ---- 并发结批拒绝过期版本 ----

def test_stale_version_rejected(store):
    settle(store, batch_id="b1")
    with pytest.raises(DomainError) as err:
        settle(store, batch_id="b2", expected_version=0)
    assert err.value.code == "STALE_VERSION"
    assert settle(store, batch_id="b2", expected_version=1)["version"] == 2


def test_stale_batch_id_cannot_be_reused(store):
    settle(store, batch_id="b1")
    insert_settling(store, "b2", 0)  # 并发残留，版本已过期
    service.recover(store)           # 标记 STALE
    with pytest.raises(DomainError) as err:
        settle(store, batch_id="b2", expected_version=1)
    assert err.value.code == "STALE_VERSION"


# ---- 重试幂等 ----

def test_retry_idempotent_no_double_apply(store):
    first = settle(store, batch_id="b1")
    again = settle(store, batch_id="b1")
    assert again["idempotent_replay"] is True
    assert again["owed_after"] == first["owed_after"]
    assert store.pool_version("P") == 1
    assert {r["project_id"]: r["owed"] for r in store.ledger("P")} == first["owed_after"]


# ---- 中断恢复 ----

def test_recover_interrupted_batch(store):
    settle(store, batch_id="b1")
    insert_settling(store, "b2", 1)  # 中断残留的未完裁决
    assert service.recover(store) == [{"batch_id": "b2", "status": "SETTLED", "replay": False}]
    assert store.pool_version("P") == 2
    assert store.batch("b2")["status"] == "SETTLED"
    assert service.recover(store) == []  # 恢复幂等，不重复扣补
    assert store.pool_version("P") == 2
    assert {r["project_id"]: r["owed"] for r in store.ledger("P")} == store.batch("b2")["result"]["owed_after"]


def test_recover_marks_stale_without_applying(store):
    settle(store, batch_id="b1")
    insert_settling(store, "b3", 0)  # 过期版本的中断批次
    before = {r["project_id"]: r["owed"] for r in store.ledger("P")}
    assert service.recover(store) == [{"batch_id": "b3", "status": "STALE_VERSION"}]
    assert store.batch("b3")["status"] == "STALE"
    assert store.pool_version("P") == 1
    assert {r["project_id"]: r["owed"] for r in store.ledger("P")} == before


# ---- 已结批次按当时依据复算，不回改 ----

def test_verify_frozen_batch_not_rewritten(store):
    first = settle(store, batch_id="b1")
    assert service.verify(store, "b1")["consistent"] is True
    settle(store, batch_id="b2", expected_version=1)  # 后续批次推进账本
    assert service.verify(store, "b1")["consistent"] is True  # 旧批按当时依据复算仍一致
    assert store.batch("b1")["result"]["owed_after"] == first["owed_after"]


def test_verify_rejects_unsettled(store):
    insert_settling(store, "b9", 0)
    with pytest.raises(DomainError):
        service.verify(store, "b9")


# ---- API 端到端 ----

def test_settle_api_flow(client):
    first = client.post("/api/remainders/settle", json={}).json()
    assert first["status"] == "READY" and first["idempotent_replay"] is False
    replay = client.post("/api/remainders/settle", json={}).json()
    assert replay["idempotent_replay"] is True and replay["batch_id"] == first["batch_id"]
    ledger = client.get("/api/remainders/ledger").json()
    assert ledger["pools"][0]["version"] == 1 and len(ledger["ledger"]) == 3
    batches = client.get("/api/remainders/batches").json()["batches"]
    assert len(batches) == 1 and batches[0]["status"] == "SETTLED"
    detail = client.get(f"/api/remainders/batches/{first['batch_id']}").json()
    assert len(detail["result"]["rationale"]) == 3
    assert client.post(f"/api/remainders/batches/{first['batch_id']}/verify").json()["consistent"] is True
    assert client.post("/api/remainders/recover").json() == {"recovered": []}


def test_settle_api_stale_version(client):
    client.post("/api/remainders/settle", json={})
    stale = client.post("/api/remainders/settle", json={"batch_id": "b-x", "expected_version": 0})
    assert stale.status_code == 422 and stale.json()["error"] == "STALE_VERSION"


def test_remainders_page(client):
    client.post("/api/remainders/settle", json={})
    html = client.get("/remainders").text
    assert "资金池结批" in html and "欠分账本" in html and "批次与补分依据" in html
