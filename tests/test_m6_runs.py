import pytest
from app.modules.m6_runs.core import SAMPLE, csv_text, run
class Store:
    def __init__(self): self.x=None
    def record(self,d,r,v): self.x=self.x or (d,r,v); return {"run_id":self.x[1],"result":self.x[2]}
def test_csv_header(): assert csv_text(SAMPLE["rows"]).startswith("project_id,amount,reason")
def test_balanced(): assert run({})["balanced"] is True
def test_total(): assert run({})["allocated_total"]=="1000.00"
def test_stable_digest(): assert run({})["digest"]==run({})["digest"]
def test_trap_1(): # TRAP-14
    s=Store(); assert run({"store":s})["run_id"]==run({"store":s})["run_id"]
def test_trap_2():
    with pytest.raises(ValueError): run({"version":1,"expected_version":2})
def test_difference(): assert run({"approved":"999.00"})["reason"]=="DIFF"
def test_row_count(): assert run({})["input_count"]==3
