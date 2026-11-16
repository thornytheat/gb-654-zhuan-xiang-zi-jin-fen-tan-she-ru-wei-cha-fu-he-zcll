from decimal import Decimal, InvalidOperation
SAMPLE={"rows":[{"project_id":"000101","amount":"1,200.50","unit":"元","weight":"2","cap":"900"},{"project_id":"9007199254740993","amount":"0.08","unit":"万元","weight":"1","cap":"800"},{"project_id":"BAD","amount":"N/A","unit":"元","weight":"-1","cap":"0"}]}
NULLS={"","N/A","NULL","-"}
def money(value, unit="元"):
    if str(value).strip() in NULLS: raise ValueError("EMPTY_VALUE")
    try: amount=Decimal(str(value).replace(",",""))
    except InvalidOperation: raise ValueError("INVALID_VALUE")
    if unit=="万元": amount*=Decimal("10000")
    elif unit!="元": raise ValueError("INVALID_UNIT")
    return amount.quantize(Decimal("0.01"))
def parse(rows):
    good=[]; bad=[]
    for line,row in enumerate(rows,2):
        try:
            weight=Decimal(str(row["weight"])); cap=money(row["cap"]); amount=money(row["amount"],row.get("unit","元"))
            if weight<0: raise ValueError("NEGATIVE_WEIGHT")
            good.append({"project_id":str(row["project_id"]),"amount":amount,"weight":weight,"cap":cap,"source_line":line})
        except (KeyError,ValueError,InvalidOperation) as exc: bad.append({"source_line":line,"reason":str(exc),"raw":row})
    return good,bad
def run(payload):
    rows=payload.get("rows",SAMPLE["rows"]); good,bad=parse(rows); return {"status":"READY","input_count":len(rows),"valid_count":len(good),"quarantine_count":len(bad),"total_yuan":str(sum((x["amount"] for x in good),Decimal(0))),"first_id":good[0]["project_id"],"reason":bad[0]["reason"] if bad else "OK"}
