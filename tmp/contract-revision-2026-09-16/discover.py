import sys,json,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from apollo import request,receipt
batch=json.loads(Path('campaigns/contract-2026-09-16/reviews/september-16-selected-30/batch.json').read_text())
jobs=[]
for e in batch['emails']:
 c,a,p=e['contact_id'].split('/');base=Path('campaigns')/c;brief=json.loads((base/'accounts'/a/'research.json').read_text());domain=brief['company']['domain']
 payload={'q_organization_domains_list':[domain],'person_titles':['engineering','engineer','robotics','autonomy','planning','optimization','science','scientist','CTO','technology','technical','research','product'],'include_similar_titles':True,'page':1,'per_page':100}
 jobs.append((e,base,a,domain,payload))
def work(j):
 try:return request('mixed_people/api_search',j[4])
 except Exception as e:return {'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(work,jobs))
records=[]
for j,response in zip(jobs,results):
 e,base,a,domain,payload=j;sid,at=receipt(base,'mixed_people/api_search',payload,response)
 target=base/'accounts'/a/'technical-owner-discovery-2026-09-16.json';target.write_text(json.dumps({'source_id':sid,'observed_at':at,'request':payload,'response':response},indent=2));target.chmod(0o600)
 people=response.get('people',[]);rec={'account':a,'campaign':base.name,'domain':domain,'source_id':sid,'total':response.get('total_entries'),'error':response.get('error'),'people':people};records.append(rec)
 print(json.dumps({'account':a,'total':rec['total'],'error':rec['error'],'people':[{'id':p.get('id'),'name':p.get('name') or (str(p.get('first_name'))+' '+str(p.get('last_name_obfuscated'))),'title':p.get('title'),'company':(p.get('organization') or {}).get('name'),'has_email':p.get('has_email')} for p in people[:35]]}))
Path('tmp/contract-revision-2026-09-16/discovery.json').write_text(json.dumps(records,indent=2))
