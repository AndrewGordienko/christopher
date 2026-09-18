import sys,json,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
D={a['account']:a for a in json.load(open('tmp/contract-revision-2026-09-16/discovery.json'))}
jobs=[('electric-era',{'id':'60ff290b9519740001f9b98f'}),('spare',{'id':'649c320cf41ea8000114d8c9'}),('open-ocean-robotics',{'id':'5dda0ee27ccf2800016963d3'}),('inorbit',{'name':'Hernan Badenes'}),('amperon',{'id':'66f769a2fb34c20001e40c44'})]
def work(j):
 a,p=j;p.update(domain=D[a]['domain'],reveal_personal_emails=False,reveal_phone_number=False,run_waterfall_email=False,run_waterfall_phone=False)
 try:return request('people/match',p)
 except Exception as e:return {'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(work,jobs))
records=[]
for (a,p),r in zip(jobs,results):
 sid,at=receipt(Path('campaigns')/D[a]['campaign'],'people/match',p,r);person=r.get('person') or {};org=person.get('organization') or {}
 records.append({'account':a,'campaign':D[a]['campaign'],'domain':D[a]['domain'],'reason':'Direct relevant technical or product owner, verify current employer before use.','source_id':sid,'observed_at':at,'person':person,'error':r.get('error')})
 print(json.dumps({'account':a,'name':person.get('name'),'title':person.get('title'),'company':org.get('name'),'domain':org.get('primary_domain'),'email':person.get('email'),'email_status':person.get('email_status'),'linkedin_url':person.get('linkedin_url'),'location':{k:person.get(k) for k in ('city','state','country')}}))
Path('tmp/contract-revision-2026-09-16/enriched2.json').write_text(json.dumps(records,indent=2))
