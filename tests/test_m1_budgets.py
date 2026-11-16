import pytest
from decimal import Decimal
from app.modules.m1_budgets.core import SAMPLE, money, parse, run
def test_trap_1(): # TRAP-05, TRAP-19
    assert money("1,200.50")==Decimal("1200.50")
def test_trap_2(): assert money("0.08","万元")==Decimal("800.00")
def test_empty_rejected():
    with pytest.raises(ValueError): money("N/A")
def test_unknown_unit():
    with pytest.raises(ValueError): money("1","美元")
def test_id_preserved(): assert parse(SAMPLE["rows"])[0][0]["project_id"]=="000101"
def test_large_id_preserved(): assert parse(SAMPLE["rows"])[0][1]["project_id"]=="9007199254740993"
def test_negative_weight_bad(): assert len(parse(SAMPLE["rows"])[1])==1
def test_accounting():
    out=run({}); assert out["input_count"]==out["valid_count"]+out["quarantine_count"]
