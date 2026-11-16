import csv, io
from decimal import Decimal
from app.manifest import canonical_digest, run_id
SAMPLE={"store":None,"version":2,"expected_version":2,"rows":[{"project_id":"A","amount":"300.00","reason":"CAP"},{"project_id":"B","amount":"420.00","reason":"WEIGHT"},{"project_id":"C","amount":"280.00","reason":"WEIGHT"}],"approved":"1000.00"}
def csv_text(rows):
    out=io.StringIO(); w=csv.DictWriter(out,fieldnames=["project_id","amount","reason"],lineterminator="\n"); w.writeheader(); w.writerows(rows); return out.getvalue()
def run(payload):
    d=SAMPLE|payload
    if int(d["version"])!=int(d["expected_version"]): raise ValueError("STALE_VERSION")
    rows=d["rows"]; total=sum((Decimal(x["amount"]) for x in rows),Decimal(0)); approved=Decimal(d["approved"]); digest=canonical_digest(rows); rid=run_id(rows); result={"input_count":len(rows),"valid_count":len(rows),"quarantine_count":0,"allocated_total":str(total),"approved":str(approved),"balanced":total==approved}; store=d.get("store")
    if store: rid=store.record(digest,rid,result)["run_id"]
    return {"status":"READY","run_id":rid,"digest":digest,"csv":csv_text(rows),**result,"reason":"OK" if total==approved else "DIFF"}
