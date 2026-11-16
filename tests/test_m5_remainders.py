from decimal import Decimal
from app.modules.m5_remainders.core import largest_remainder, run
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
