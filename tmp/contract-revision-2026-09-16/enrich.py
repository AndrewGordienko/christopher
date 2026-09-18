import sys,json,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
short=json.load(open('tmp/contract-revision-2026-09-16/shortlist.json'));discover={a['account']:a for a in json.load(open('tmp/contract-revision-2026-09-16/discovery.json'))}
jobs=[]
for a,p in short.items():
 d=discover[a];payload={k:v for k,v in p.items() if k in ('id','name')};payload.update(domain=d['domain'],reveal_personal_emails=False,reveal_phone_number=False,run_waterfall_email=False,run_waterfall_phone=False);jobs.append((a,p,d,payload))
def work(j):
 try:return request('people/match',j[3])
 except Exception as e:return {'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(work,jobs))
records=[]
for j,response in zip(jobs,results):
 a,p,d,payload=j;sid,at=receipt(Path('campaigns')/d['campaign'],'people/match',payload,response);person=response.get('person') or {};org=person.get('organization') or {}
 record={'account':a,'campaign':d['campaign'],'domain':d['domain'],'reason':p['reason'],'source_id':sid,'observed_at':at,'person':person,'error':response.get('error')};records.append(record)
 print(json.dumps({'account':a,'name':person.get('name'),'title':person.get('title'),'company':org.get('name'),'domain':org.get('primary_domain'),'employees':org.get('estimated_num_employees'),'email':person.get('email'),'email_status':person.get('email_status'),'linkedin_url':person.get('linkedin_url'),'location':{k:person.get(k) for k in ('city','state','country')},'error':record['error']}))
Path('tmp/contract-revision-2026-09-16/enriched.json').write_text(json.dumps(records,indent=2))
