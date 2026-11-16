from decimal import Decimal
SAMPLE={"total":"1000.00","items":[{"id":"A","weight":"5","cap":"300.00"},{"id":"B","weight":"3","cap":"500.00"},{"id":"C","weight":"2","cap":"500.00"}]}
def allocate(total, items):
    remaining=Decimal(str(total)); pending={str(x["id"]):{"weight":Decimal(str(x["weight"])),"cap":Decimal(str(x["cap"]))} for x in items}; out={k:Decimal(0) for k in pending}
    while pending and remaining>0:
        total_weight=sum((x["weight"] for x in pending.values()),Decimal(0))
        if total_weight<=0: break
        capped=[]
        for key,item in pending.items():
            proposal=remaining*item["weight"]/total_weight
            room=item["cap"]-out[key]
            if proposal>=room: out[key]+=room; capped.append(key)
        if not capped:
            for key,item in pending.items(): out[key]+=remaining*item["weight"]/total_weight
            remaining=Decimal(0); break
        remaining=Decimal(str(total))-sum(out.values())
        for key in capped: pending.pop(key)
    return out,remaining
def run(payload):
    d=SAMPLE|payload; out,left=allocate(d["total"],d["items"]); return {"status":"READY","input_count":len(out),"valid_count":len(out),"quarantine_count":0,"allocated":{k:str(v) for k,v in out.items()},"allocated_total":str(sum(out.values())),"unallocated":str(left),"reason":"OK" if left==0 else "CAP_LIMIT"}
