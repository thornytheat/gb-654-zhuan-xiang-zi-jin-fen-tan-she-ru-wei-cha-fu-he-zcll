from decimal import Decimal
SAMPLE={"items":[{"id":"A","weight":"2"},{"id":"B","weight":"1"},{"id":"C","weight":"0"}]}
def normalize(items):
    weights=[Decimal(str(x["weight"])) for x in items]
    if any(x<0 for x in weights): raise ValueError("NEGATIVE_WEIGHT")
    total=sum(weights,Decimal(0))
    if total==0: raise ValueError("ZERO_WEIGHT_GROUP")
    return [{"id":item["id"],"weight":weight,"share":weight/total} for item,weight in zip(items,weights)]
def run(payload):
    items=payload.get("items",SAMPLE["items"]); out=normalize(items); return {"status":"READY","input_count":len(out),"valid_count":len(out),"quarantine_count":0,"share_sum":str(sum((x["share"] for x in out),Decimal(0)).normalize()),"shares":{x["id"]:str(x["share"]) for x in out},"reason":"OK"}
