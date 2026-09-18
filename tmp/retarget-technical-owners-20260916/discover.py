import json, sqlite3, sys, shutil, concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request, receipt
from research import write_json

root=Path('tmp/retarget-technical-owners-20260916')
review=Path('campaigns/contract-2026-09-16/reviews/technical-owners-2026-09-16')
review.mkdir(parents=True,exist_ok=True)
accounts='axle agtonomy bonsai-robotics bearing-ai spoor glacier terraclear timefold coiled toffeex-marco ev-energy-steve flash-forest atmo treefera chloris rugged civ-robotics foxglove vsp-aaike assaia neural-concept augmentus duality albert realtime-robotics orchard gideon carbonrobotics'.split()
db=sqlite3.connect('.runtime/outbound.sqlite3'); db.row_factory=sqlite3.Row
assert not (review/'before.sqlite3').exists(), 'Already initialized; do not repeat'
with sqlite3.connect(review/'before.sqlite3') as dest: db.backup(dest)
rows=[]; now=datetime.now(timezone.utc).isoformat()
for a in accounts:
    matches=db.execute("select c.*,s.id action_id,s.status queue_status,s.body queue_body,s.subject queue_subject,s.queue_date,s.send_at queue_send_at from contacts c join scheduled_sends s on c.id=s.contact_id where c.account_id=? and c.engine='technical_contract' and s.touch_number=1 and s.status in ('review','held','approved','gmail_scheduled','cancel_required')",(a,)).fetchall()
    assert len(matches)==1,(a,len(matches))
    r=dict(matches[0]); assert r['touch_number']==0 and not r['last_outbound_at'] and not r['last_inbound_at'] and r['queue_status'] in ('review','held'),a
    assert not db.execute("select 1 from gmail_executions where action_id=? and state in ('claimed','reconcile','completed','cancel_required')",(r['action_id'],)).fetchone(),a
    base=Path('campaigns')/r['campaign']/'accounts'/a
    b=json.loads((base/'research.json').read_text()); r['domain']=b['company']['domain']
    dst=review/'source-before'/r['campaign']/a; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(base,dst)
    rows.append(r)
write_json(root/'before.json',rows); write_json(review/'before.json',rows)
with db:
    for r in rows:
        ctx=json.loads(r['context']);ctx.update(draft_hold=True)
        reason='User requested technical-owner retargeting; held locally until recipient research and exact draft review are complete.'
        db.execute("update contacts set context=?,next_action_at=NULL,recommended_action='WAIT',decision=?,updated_at=? where id=?",(json.dumps(ctx),json.dumps({'action':'WAIT','reason':reason}),now,r['id']))
        db.execute("update scheduled_sends set status='held',reviewed_at=NULL,decision=? where id=?",(json.dumps({'reason':reason,'sending_authorized':False}),r['action_id']))
        db.execute('delete from execution_approvals where action_id=?',(r['action_id'],))
db.close()
jobs=[]
for r in rows:
    jobs.append({'account':r['account_id'],'campaign':r['campaign'],'domain':r['domain'],'kind':'contract'})
for a,d in [('waabi','waabi.ai'),('kepler','kepler.space'),('ecobee','ecobee.com'),('peak-power','peakpowerenergy.com'),('tiny-mile','tinymile.ai'),('rbc-borealis','borealisai.com')]:
    jobs.append({'account':a,'domain':d,'campaign':'toronto-january-2027-jobs','kind':'employment'})
titles=['engineering','engineer','science','scientist','research','developer','autonomy','planning','simulation','optimization','software','technical','CTO','product']
def call(j):
    p={'q_organization_domains_list':[j['domain']],'person_titles':titles,'include_similar_titles':True,'page':1,'per_page':100}
    try:return p,request('mixed_people/api_search',p)
    except Exception as e:return p,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: responses=list(pool.map(call,jobs))
records=[]
for j,(p,v) in zip(jobs,responses):
    sid,at=receipt(Path('campaigns')/j['campaign'],'mixed_people/api_search',p,v)
    rec={**j,'source_id':sid,'observed_at':at,'people':v.get('people',[]),'total_entries':v.get('total_entries'),'error':v.get('error')};records.append(rec)
    write_json(Path('campaigns')/j['campaign']/'accounts'/j['account']/'technical-owner-discovery-20260916.json',rec)
write_json(root/'discovery.json',records)
for r in records:
    print(r['account'],r['total_entries'],r['error'])
    for p in r['people']:
        print(' ',p.get('id'),p.get('first_name'),p.get('last_name_obfuscated'),p.get('title'),p.get('has_email'))
