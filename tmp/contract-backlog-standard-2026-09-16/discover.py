import json,sys,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
rows=json.load(open('tmp/contract-backlog-standard-2026-09-16/rows.json'))
jobs=[]
for a in ('marinelabs','terraclear','flash-forest','scanifly','uncountable'):
 r=next(r for r in rows if r['account_id']==a);b=json.load(open(Path('campaigns')/r['campaign']/'accounts'/a/'research.json'))
 p={'q_organization_domains_list':[b['company']['domain']],'person_titles':['engineering','technical','software','robotics','autonomy','science','research','CTO','product'],'include_similar_titles':True,'page':1,'per_page':100};jobs.append((r,p))
def call(j):
 try:return request('mixed_people/api_search',j[1])
 except Exception as e:return {'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(call,jobs))
records=[]
for (r,p),v in zip(jobs,responses):
 sid,at=receipt(Path('campaigns')/r['campaign'],'mixed_people/api_search',p,v);records.append({'account':r['account_id'],'campaign':r['campaign'],'domain':p['q_organization_domains_list'][0],'source_id':sid,'observed_at':at,'people':v.get('people',[]),'error':v.get('error')})
 print(r['account_id'],json.dumps([{k:x.get(k) for k in ('id','first_name','last_name_obfuscated','title','has_email')} for x in v.get('people',[]) if any(t in x.get('title','').lower() for t in ('head','lead','cto','chief','vp','director','manager'))]))
Path('tmp/contract-backlog-standard-2026-09-16/discovery.json').write_text(json.dumps(records,indent=2))
