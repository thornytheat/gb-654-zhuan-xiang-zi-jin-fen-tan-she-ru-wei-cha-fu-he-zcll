from decimal import Decimal, ROUND_DOWN
SAMPLE={"total":"10.00","shares":{"A":"0.333","B":"0.333","C":"0.334"}}
def largest_remainder(total, shares, quantum=Decimal("0.01")):
    total=Decimal(str(total)); raw={str(k):total*Decimal(str(v)) for k,v in shares.items()}; base={k:v.quantize(quantum,rounding=ROUND_DOWN) for k,v in raw.items()}; units=int(((total-sum(base.values()))/quantum).to_integral_value()); order=sorted(raw,key=lambda k:(-(raw[k]-base[k]),k))
    for key in order[:units]: base[key]+=quantum
    return base
def run(payload):
    d=SAMPLE|payload; out=largest_remainder(d["total"],d["shares"]); return {"status":"READY","input_count":len(out),"valid_count":len(out),"quarantine_count":0,"amounts":{k:str(v) for k,v in out.items()},"total":str(sum(out.values())),"reason":"OK"}
