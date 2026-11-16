from app.modules.m2_eligibility.core import SAMPLE, RULES, evaluate, run
def test_trap_1(): # TRAP-06, TRAP-22
    rules=list(reversed(RULES)); assert evaluate({"id":"X","blacklisted":True,"score":10,"region":"rural"},rules)["reason"]=="BLACKLIST"
def test_trap_2(): assert evaluate({"id":"A","blacklisted":False,"score":80,"region":"rural"})["eligible"] is True
def test_blacklist_wins(): assert evaluate(SAMPLE["projects"][1])["reason"]=="BLACKLIST"
def test_low_score(): assert evaluate(SAMPLE["projects"][2])["reason"]=="LOW_SCORE"
def test_default(): assert evaluate({"id":"D","score":80,"region":"urban","blacklisted":False})["reason"]=="DEFAULT"
def test_priority_exposed(): assert evaluate(SAMPLE["projects"][1])["priority"]==100
def test_run_counts(): assert run({})["input_count"]==3
def test_run_rejected(): assert run({})["quarantine_count"]==2
