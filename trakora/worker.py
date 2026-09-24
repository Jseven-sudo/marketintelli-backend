import os,time,json,hashlib
from datetime import datetime,timezone,timedelta
from dateutil.parser import parse as dtparse
import requests,psycopg2
from psycopg2.extras import Json

DB=os.environ["DATABASE_URL"]
INTERVAL=int(os.environ.get("INGEST_INTERVAL_SECONDS","21600"))
API="https://ocds-api.etenders.gov.za/api/OCDSReleases"

AUTO=["vehicle","automotive","motor","bakkie","truck","bus","fleet","tyre","tire","battery","batteries","lubricant","oil","filter","brake","clutch","gearbox","differential","propshaft","turbo","injector","radiator","spare","workshop","auto electrical","towing","breakdown","recovery","tractor","plant","earthmoving","telematics"]
ADJ=["cartridge","stationery","ppe","protective clothing","cleaning consumable","general consumable","office supply"]
LOW_WC=["tyre","battery","lubricant","filter","spare","cartridge","stationery","ppe","consumable"]
SERVICE=["maintenance","repair","overhaul","fitment","towing","breakdown","fleet management","telematics"]

def get_conn():
    return psycopg2.connect(DB)

def iso(v):
    if not v:
        return None
    try:
        return dtparse(v)
    except Exception:
        return None

def buyer_name(r):
    b=r.get("buyer")
    if isinstance(b,dict) and b.get("name"):
        return b["name"]
    for p in r.get("parties") or []:
        if "buyer" in (p.get("roles") or []):
            return p.get("name") or "Unknown"
    return "Unknown"

def tender_of(r):
    t=r.get("tender")
    return t if isinstance(t,dict) else {}

def briefing_of(t):
    b=t.get("briefingSession")
    return b if isinstance(b,dict) else {}

def textblob(r):
    t=tender_of(r)
    vals=[t.get("title"),t.get("description"),t.get("category"),t.get("mainProcurementCategory"),
          t.get("province"),t.get("deliveryLocation"),t.get("specialConditions"),t.get("eligibilityCriteria"),buyer_name(r)]
    for i in t.get("items") or []:
        if isinstance(i,dict):
            vals.append(i.get("description"))
    return " ".join(str(x) for x in vals if x).lower()

def match(r):
    b=textblob(r)
    return any(k in b for k in AUTO) or any(k in b for k in ADJ)

def score(r):
    t=tender_of(r); b=textblob(r)
    auto=sum(1 for k in AUTO if k in b); adj=sum(1 for k in ADJ if k in b)
    fit=min(100,35+auto*12 if auto else 25+adj*10)
    margin=70 if any(k in b for k in ["spare","turbo","injector","gearbox","differential","auto electrical"]) else 55
    capital=85 if any(k in b for k in LOW_WC) else 55
    execution=45 if any(k in b for k in SERVICE) else 80
    end=iso((t.get("tenderPeriod") or {}).get("endDate"))
    days=(end-datetime.now(timezone.utc)).total_seconds()/86400 if end else 14
    deadline=90 if days>=10 else 70 if days>=5 else 45 if days>=2 else 15
    briefing=briefing_of(t)
    bat=iso(briefing.get("date"))
    missed=bool(briefing.get("compulsory") and bat and bat<datetime.now(timezone.utc))
    total=round(.30*fit+.20*margin+.20*capital+.15*execution+.15*deadline,1)
    if missed:
        decision,status="no_bid","ineligible"
    elif end and end<datetime.now(timezone.utc):
        decision,status="no_bid","expired"
    elif total>=70 and execution>=65:
        decision,status="bid","live"
    elif total>=62:
        decision,status=("partner" if execution<65 else "watch"),"live"
    else:
        decision,status="watch","live"
    if missed:
        action="Missed compulsory briefing — retain as history."
    elif decision=="bid":
        action="Source at least 3 suppliers, verify specification/returnables and model cash trough."
    elif decision=="partner":
        action="Find qualified delivery partner and verify subcontract/JV eligibility."
    else:
        action="Verify primary tender pack before committing bid resources."
    return fit,margin,capital,execution,deadline,total,decision,status,action

def normalize(r):
    t=tender_of(r)
    briefing=briefing_of(t)
    docs=t.get("documents") or []
    source=next((d.get("url") for d in docs if isinstance(d,dict) and d.get("url")),None)
    methods=t.get("submissionMethod") or []
    if isinstance(methods,str):
        methods=[methods]
    fit,margin,capital,execution,deadline,total,decision,status,action=score(r)
    return dict(
      ocid=r.get("ocid") or r.get("id"),
      release_id=r.get("id"),
      tender_id=t.get("id"),
      buyer_name=buyer_name(r),
      title=t.get("title") or r.get("description") or "Untitled procurement",
      description=t.get("description"),
      category=t.get("category") or t.get("mainProcurementCategory"),
      province=t.get("province"),
      delivery_location=t.get("deliveryLocation"),
      procurement_method=t.get("procurementMethod") or t.get("procurementMethodDetails"),
      published_at=iso(r.get("date")),
      closing_at=iso((t.get("tenderPeriod") or {}).get("endDate")),
      briefing_required=bool(briefing.get("isSession")),
      briefing_compulsory=bool(briefing.get("compulsory")),
      briefing_at=iso(briefing.get("date")),
      briefing_venue=briefing.get("venue"),
      submission_method=", ".join(str(x) for x in methods if x),
      submission_details=t.get("submissionMethodDetails"),
      eligibility_criteria=t.get("eligibilityCriteria"),
      special_conditions=t.get("specialConditions"),
      source_url=source,
      documents=docs,
      raw=r,
      status=status,
      bid_decision=decision,
      fit_score=fit,
      margin_score=margin,
      capital_score=capital,
      execution_score=execution,
      deadline_score=deadline,
      total_score=total,
      recommended_action=action,
      needs_primary_verification=not bool(source)
    )

def upsert(cur,n):
    if not n.get("ocid"):
        return "rejected"
    rawtxt=json.dumps(n["raw"],sort_keys=True,default=str,separators=(",",":"))
    h=hashlib.sha256(rawtxt.encode()).hexdigest()
    cur.execute("select id,content_hash from opportunities where ocid=%s",(n["ocid"],))
    row=cur.fetchone()
    fields=[k for k in n if k not in ("ocid","raw")]
    if not row:
        cols=["ocid"]+fields+["raw","content_hash"]
        vals=[n["ocid"]]+[n[k] for k in fields]+[Json(n["raw"]),h]
        cur.execute("insert into opportunities ("+",".join(cols)+") values ("+",".join(["%s"]*len(vals))+") returning id",vals)
        oid=cur.fetchone()[0]
        cur.execute("insert into opportunity_versions(opportunity_id,content_hash,raw) values(%s,%s,%s)",(oid,h,Json(n["raw"])))
        return "inserted"
    oid,old=row
    if old==h:
        cur.execute("update opportunities set last_seen_at=now() where id=%s",(oid,))
        return "same"
    sets=",".join(k+"=%s" for k in fields)
    vals=[n[k] for k in fields]+[Json(n["raw"]),h,oid]
    cur.execute("update opportunities set "+sets+",raw=%s,content_hash=%s,last_seen_at=now(),updated_at=now() where id=%s",vals)
    cur.execute("insert into opportunity_versions(opportunity_id,content_hash,raw) values(%s,%s,%s) on conflict do nothing",(oid,h,Json(n["raw"])))
    return "updated"

def seed():
    try:
        data=json.load(open("/app/seed.json"))
    except Exception as e:
        print("seed_load_failed",e,flush=True); return
    with get_conn() as c,c.cursor() as cur:
        for r in data:
            raw={"seed":True,**r}
            n=dict(
              ocid=r["ocid"],release_id=None,tender_id=r.get("tender_id"),buyer_name=r["buyer_name"],title=r["title"],
              description=r.get("description"),category=r.get("category"),province=r.get("province"),delivery_location=r.get("delivery_location"),
              procurement_method=None,published_at=iso(r.get("published_at")),closing_at=iso(r.get("closing_at")),
              briefing_required=r.get("briefing_required",False),briefing_compulsory=r.get("briefing_compulsory",False),
              briefing_at=iso(r.get("briefing_at")),briefing_venue=r.get("briefing_venue"),submission_method=r.get("submission_method"),
              submission_details=r.get("submission_details"),eligibility_criteria=r.get("eligibility_criteria"),special_conditions=None,
              source_url=r.get("source_url"),documents=[],raw=raw,status=r.get("status","live"),bid_decision=r.get("bid_decision","watch"),
              fit_score=r.get("fit_score",50),margin_score=r.get("margin_score",50),capital_score=r.get("capital_score",50),
              execution_score=r.get("execution_score",50),deadline_score=r.get("deadline_score",50),total_score=r.get("total_score",50),
              recommended_action=r.get("recommended_action","Verify primary source."),needs_primary_verification=True
            )
            upsert(cur,n)

def ingest():
    start=datetime.now(timezone.utc)-timedelta(days=3)
    end=datetime.now(timezone.utc)+timedelta(days=1)
    with get_conn() as c,c.cursor() as cur:
        cur.execute("insert into ingest_runs(source_name) values('National Treasury OCDS API') returning id")
        run_id=cur.fetchone()[0]; c.commit()
    fetched=matched=ins=upd=rej=0
    try:
        for page in range(1,51):
            resp=requests.get(API,params={"PageNumber":page,"PageSize":1000,"dateFrom":start.date().isoformat(),"dateTo":end.date().isoformat()},timeout=120)
            resp.raise_for_status()
            pkg=resp.json()
            rels=pkg.get("releases") or pkg.get("Releases") or []
            if not rels:
                break
            fetched+=len(rels)
            with get_conn() as c,c.cursor() as cur:
                for r in rels:
                    try:
                        if not match(r):
                            rej+=1; continue
                        matched+=1
                        res=upsert(cur,normalize(r))
                        ins+=int(res=="inserted"); upd+=int(res=="updated")
                    except Exception as e:
                        rej+=1; print("release_error",r.get("ocid"),e,flush=True)
            if len(rels)<1000:
                break
        with get_conn() as c,c.cursor() as cur:
            cur.execute("update ingest_runs set completed_at=now(),fetched=%s,matched=%s,inserted=%s,updated=%s,rejected=%s,status='completed' where id=%s",
                        (fetched,matched,ins,upd,rej,run_id))
        print("ingest",fetched,matched,ins,upd,rej,flush=True)
    except Exception as e:
        with get_conn() as c,c.cursor() as cur:
            cur.execute("update ingest_runs set completed_at=now(),status='failed',error_summary=%s where id=%s",(str(e)[:1000],run_id))
        print("ingest_failed",e,flush=True)

if __name__=="__main__":
    time.sleep(8)
    seed()
    while True:
        ingest()
        time.sleep(INTERVAL)
