import os
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse

DB=os.environ["DATABASE_URL"]
TOKEN=os.environ.get("ADMIN_TOKEN","")
app=FastAPI(title="Trakora OS",version="0.1.0")

def get_conn():
    return psycopg2.connect(DB)

@app.get("/health")
def health():
    with get_conn() as c, c.cursor() as cur:
        cur.execute("select 1")
        cur.fetchone()
    return {"status":"ok","service":"trakora-os","time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/metrics")
def metrics():
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""select
          count(*) filter (where status='live' and (closing_at is null or closing_at>now())) as live,
          count(*) filter (where status='live' and bid_decision='bid' and (closing_at is null or closing_at>now())) as bid,
          count(*) filter (where status='live' and bid_decision='partner' and (closing_at is null or closing_at>now())) as partner,
          count(*) filter (where needs_primary_verification and status='live' and (closing_at is null or closing_at>now())) as verify,
          count(*) filter (where status='live' and closing_at between now() and now()+interval '72 hours') as urgent,
          count(*) as total
        from opportunities""")
        return dict(cur.fetchone())

@app.get("/api/opportunities")
def opportunities(decision:str|None=None,status:str="live",limit:int=200):
    clauses=["status=%s"]; params=[status]
    if decision:
        clauses.append("bid_decision=%s"); params.append(decision)
    params.append(min(max(limit,1),1000))
    query="""select id,ocid,tender_id,buyer_name,title,description,category,province,delivery_location,
      published_at,closing_at,briefing_required,briefing_compulsory,briefing_at,briefing_venue,
      submission_method,submission_details,eligibility_criteria,special_conditions,source_url,documents,
      status,bid_decision,fit_score,margin_score,capital_score,execution_score,deadline_score,total_score,
      recommended_action,needs_primary_verification,first_seen_at,last_seen_at,updated_at
      from opportunities where """+" and ".join(clauses)+"""
      order by closing_at nulls last,total_score desc limit %s"""
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query,params)
        return [dict(x) for x in cur.fetchall()]

@app.post("/api/opportunities/{opportunity_id}/decision")
def set_decision(opportunity_id:int,payload:dict,authorization:str|None=Header(default=None)):
    if not TOKEN or authorization!=f"Bearer {TOKEN}":
        raise HTTPException(401,"Unauthorized")
    decision=payload.get("bid_decision")
    if decision not in {"bid","partner","watch","no_bid"}:
        raise HTTPException(400,"Invalid decision")
    with get_conn() as c, c.cursor() as cur:
        cur.execute("update opportunities set bid_decision=%s,recommended_action=coalesce(%s,recommended_action),updated_at=now() where id=%s returning id",
                    (decision,payload.get("recommended_action"),opportunity_id))
        if not cur.fetchone():
            raise HTTPException(404,"Not found")
    return {"ok":True}

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Trakora Procurement Command</title><style>
body{font-family:Arial,sans-serif;background:#f5f1e8;color:#171717;margin:0}main{max-width:1400px;margin:auto;padding:28px}
header{border-bottom:1px solid #bbb4a8;padding-bottom:18px}h1{font-family:Georgia,serif;font-size:42px;margin:8px 0}.ey{font-size:11px;letter-spacing:.12em;color:#2457d6}
.metrics{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid #bbb4a8}.m{padding:18px;border-right:1px solid #ccc5b9}.m b{display:block;font-size:28px}.m span{font-size:11px;color:#666}
.toolbar{display:flex;gap:8px;margin:18px 0}button{background:#fff;border:1px solid #aaa;padding:8px 12px;cursor:pointer}.active{background:#2457d6;color:white}
.card{background:#fbf9f4;border:1px solid #d0c9bd;padding:18px;margin:10px 0}.top{display:flex;justify-content:space-between;gap:20px}.ref{font:12px monospace;color:#2457d6}.tags span{border:1px solid #aaa;padding:4px 6px;margin-left:4px;font-size:10px}.verify{color:#8a6411}.urgent{color:#a33}.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;font-size:12px}.next{border-top:1px solid #ddd5c8;margin-top:12px;padding-top:10px}
@media(max-width:800px){.metrics{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.top{display:block}}
</style></head><body><main><header><div class="ey">TRAKORA · AUTOMOTIVE SUPPLY &amp; FLEET SOLUTIONS</div><h1>Procurement Command</h1><div>Discover → verify → source → price → bid → collect. Permanent opportunity intelligence.</div></header>
<section class="metrics" id="metrics"></section><div class="toolbar"><button class="active" data-f="">Live</button><button data-f="bid">Bid</button><button data-f="partner">Partner</button><button data-f="watch">Watch</button></div><section id="list">Loading…</section>
<script>
let filter=''; const fmt=d=>d?new Date(d).toLocaleString('en-ZA',{timeZone:'Africa/Johannesburg'}):'—';
async function load(){const m=await fetch('/api/metrics').then(r=>r.json());document.querySelector('#metrics').innerHTML=[['Live',m.live],['Bid',m.bid],['Partner',m.partner],['Verify',m.verify],['≤72h',m.urgent],['Stored',m.total]].map(x=>'<div class=m><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('');
const u='/api/opportunities'+(filter?'?decision='+filter:'');const rows=await fetch(u).then(r=>r.json());document.querySelector('#list').innerHTML=rows.map(o=>{const urgent=o.closing_at&&new Date(o.closing_at)-Date.now()<259200000&&new Date(o.closing_at)>new Date();return '<article class=card><div class=top><div><div class=ref>'+esc(o.buyer_name)+' · '+esc(o.tender_id||o.ocid)+'</div><h2>'+esc(o.title)+'</h2></div><div class=tags><span>'+esc(o.bid_decision)+'</span>'+(o.needs_primary_verification?'<span class=verify>VERIFY</span>':'')+(urgent?'<span class=urgent>≤72H</span>':'')+'</div></div><p>'+esc(o.description||'')+'</p><div class=grid><div><b>Closes</b><br>'+fmt(o.closing_at)+'</div><div><b>Location</b><br>'+esc(o.delivery_location||o.province||'—')+'</div><div><b>Submission</b><br>'+esc(o.submission_method||'Verify')+'</div></div><div class=next><b>Next action</b><br>'+esc(o.recommended_action||'Review and qualify')+'</div></article>'}).join('')||'No matching opportunities.'}
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{document.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter=b.dataset.f;load()});load();setInterval(load,60000);
</script></main></body></html>""")
