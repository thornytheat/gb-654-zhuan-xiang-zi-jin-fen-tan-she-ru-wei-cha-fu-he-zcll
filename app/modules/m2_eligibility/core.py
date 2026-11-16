SAMPLE={"projects":[{"id":"A","region":"rural","score":82,"blacklisted":False},{"id":"B","region":"urban","score":95,"blacklisted":True},{"id":"C","region":"rural","score":55,"blacklisted":False}]}
RULES=[("BLACKLIST",100,lambda x:x.get("blacklisted",False),False),("LOW_SCORE",80,lambda x:x.get("score",0)<60,False),("RURAL",20,lambda x:x.get("region")=="rural",True),("DEFAULT",0,lambda x:True,True)]
def evaluate(project, rules=RULES):
    hits=[(priority,code,allowed) for code,priority,pred,allowed in rules if pred(project)]; priority,code,allowed=max(hits); return {"id":project["id"],"eligible":allowed,"reason":code,"priority":priority}
def run(payload):
    projects=payload.get("projects",SAMPLE["projects"]); out=[evaluate(x) for x in projects]; return {"status":"READY","input_count":len(out),"valid_count":sum(x["eligible"] for x in out),"quarantine_count":sum(not x["eligible"] for x in out),"decisions":out,"reason":"REVIEW"}
