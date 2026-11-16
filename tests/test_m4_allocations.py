from decimal import Decimal
from app.modules.m4_allocations.core import SAMPLE, allocate, run
def test_trap_1(): # TRAP-09, TRAP-26
    out,left=allocate("1000",SAMPLE["items"]); assert out["A"]==Decimal("300.00")
def test_trap_2():
    forward=allocate("1000",SAMPLE["items"])[0]; reverse=allocate("1000",list(reversed(SAMPLE["items"])))[0]; assert forward==reverse
def test_conserves():
    out,left=allocate("1000",SAMPLE["items"]); assert sum(out.values())+left==Decimal("1000")
def test_no_cap_exceeded():
    out,_=allocate("1000",SAMPLE["items"]); assert all(out[x["id"]]<=Decimal(x["cap"]) for x in SAMPLE["items"])
def test_all_caps_leave_balance():
    out,left=allocate("10",[{"id":"A","weight":1,"cap":3}]); assert left==7
def test_zero_total(): assert allocate("0",SAMPLE["items"])[1]==0
def test_run_total(): assert run({})["allocated_total"]=="1000.00"
def test_run_ok(): assert run({})["reason"]=="OK"
