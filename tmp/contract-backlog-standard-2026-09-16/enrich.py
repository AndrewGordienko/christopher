import json,sys,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
d={r['account']:r for r in json.load(open('tmp/contract-backlog-standard-2026-09-16/discovery.json'))}
d['diligent-robotics']={'campaign':'contract-2026-09-16','domain':'serverobotics.com'}
short=[('marinelabs',{'id':'60198c618e7f15000185174b'}),('terraclear',{'name':'Vivek Nayak'}),('flash-forest',{'id':'57d99e54a6da9872115e6c1d'}),('scanifly',{'id':'66f2507a0a61fc0001238821'}),('uncountable',{'id':'626edc453736e90001b8ff2d'}),('diligent-robotics',{'id':'611c16f58b1f450001fec1a8'})]
def call(j):
 a,p=j;p.update(domain=d[a]['domain'],reveal_personal_emails=False,reveal_phone_number=False,run_waterfall_email=False,run_waterfall_phone=False)
 try:return request('people/match',p)
 except Exception as e:return {'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(call,short))
out=[]
for (a,p),v in zip(short,responses):
 sid,at=receipt(Path('campaigns')/d[a]['campaign'],'people/match',p,v);person=v.get('person') or {};org=person.get('organization') or {}
 out.append({'account':a,'campaign':d[a]['campaign'],'domain':d[a]['domain'],'source_id':sid,'observed_at':at,'person':person})
 print(json.dumps({'account':a,'name':person.get('name'),'title':person.get('title'),'company':org.get('name'),'domain':org.get('primary_domain'),'email':person.get('email'),'email_status':person.get('email_status'),'city':person.get('city'),'state':person.get('state'),'country':person.get('country'),'linkedin':person.get('linkedin_url')}))
Path('tmp/contract-backlog-standard-2026-09-16/enriched.json').write_text(json.dumps(out,indent=2))
