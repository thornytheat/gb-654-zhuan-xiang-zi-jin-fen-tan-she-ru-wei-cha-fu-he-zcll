import pytest
from decimal import Decimal
from app.modules.m3_weights.core import normalize, run
def test_trap_1(): # TRAP-07, TRAP-24
    assert sum(x["share"] for x in normalize([{"id":"A","weight":2},{"id":"B","weight":1}]))==Decimal(1)
def test_trap_2(): assert normalize([{"id":"001","weight":1}])[0]["id"]=="001"
def test_negative_rejected():
    with pytest.raises(ValueError): normalize([{"id":"A","weight":-1}])
def test_zero_group_rejected():
    with pytest.raises(ValueError): normalize([{"id":"A","weight":0}])
def test_zero_member_allowed(): assert normalize([{"id":"A","weight":1},{"id":"B","weight":0}])[1]["share"]==0
def test_order_preserved(): assert [x["id"] for x in normalize([{"id":"B","weight":1},{"id":"A","weight":1}])]==["B","A"]
def test_run_sum(): assert run({})["share_sum"]=="1"
def test_run_count(): assert run({})["valid_count"]==3
