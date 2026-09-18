import json,sqlite3,sys,shutil,hashlib,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import add_source,read_sources,validate_brief,slug,write_json
from apollo import normalize_contact
root=Path('tmp/contract-backlog-standard-2026-09-16');review=Path('campaigns/contract-2026-09-16/reviews/human-progression-2026-09-16');review.mkdir(parents=True,exist_ok=True)
at=datetime.now(timezone.utc).isoformat()
assert not (review/'before.sqlite3').exists()
listed=json.load(open(root/'rows.json'));today=json.load(open('tmp/contract-revision-2026-09-16/applied.json'))
ids={r['id'] for r in listed}|{r['contact_id'] for r in today};extra=['contract-week-2026-09-17/simscale/mariano-barrios','contract-week-2026-09-17/chloris/alessandro-baccini']
with sqlite3.connect('file:.runtime/outbound.sqlite3?mode=ro',uri=True) as db,sqlite3.connect(review/'before.sqlite3') as dest:
 db.backup(dest);db.row_factory=sqlite3.Row
 rows=[dict(db.execute('select c.*,s.id action_id,s.subject queue_subject,s.body queue_body,s.status queue_status,s.queue_date,s.send_at queue_send_at from contacts c join scheduled_sends s on c.id=s.contact_id where c.id=?',(cid,)).fetchone()) for cid in sorted(ids|set(extra))]
for r in rows:
 assert r['touch_number']==0 and not r['last_inbound_at'] and not r['last_outbound_at'] and r['queue_status'] in ('review','held'),r['id']
 c,a,p=r['id'].split('/');b=Path('campaigns')/c/'accounts'/a;dst=review/'source-before'/c/a
 if not dst.exists():shutil.copytree(b,dst)
write_json(review/'before.json',rows);byid={r['id']:r for r in rows}
web=[]
def strings(v):
 if isinstance(v,str):yield v
 elif isinstance(v,dict):
  for x in v.values():yield from strings(x)
 elif isinstance(v,list):
  for x in v:yield from strings(x)
for chunkall in strings(json.load(open(root/'web-evidence.json'))):
 for chunk in chunkall.split('--------------------------------------------------------------------------------'):
  m=re.search(r'\((https?://[^\s)]+)\)',chunk)
  if m:web.append({'id':'human-web-'+hashlib.sha256(chunk.encode()).hexdigest()[:18],'url':m.group(1),'observed_at':at,'tool':'web.run','tool_ref':'captured-web-evidence-20260916','text':chunk.strip()})
for c in {r['campaign'] for r in rows}:
 for source in web:add_source(Path('campaigns')/c,source)
new={r['account']:r for r in json.load(open(root/'enriched.json')) if r['account'] in ('marinelabs','scanifly','uncountable')}
reasons={
 'marinelabs':'Bryce Bocking leads data science and coastal time-series modelling; company team page corroborates current provider role. Closer to the proposed observation/forecast evaluation than CEO.',
 'scanifly':'John Novak is the current provider-verified founder and the documented inventor/product owner of the 3D viewshed technology. Technical founder is a better route for geometry evaluation than the commercial CEO.',
 'uncountable':'Katie Bacher is the provider-verified Director of Engineering; an engineering manager can assess or route experimental-workflow evaluation. Exact optimization responsibility and budget remain unknown.',
 'simscale':'Reuse the existing provider-verified Mariano Barrios, VP Engineering, rather than approach David Heiny and Mariano in parallel.',
 'terraclear':'Retain verified technical founder Brent Frei. The alternative Mary Reeder has public technical relevance but no verified usable contact from current enrichment; Vivek match did not establish current employment.',
 'flash-forest':'Retain existing verified Bryce Jones contact. Quinn Daigle is currently technical lead but the primary interview describes seed-pod manufacturing; drone-route ownership is unconfirmed. Badriveer Thota enrichment resolves to another employer, so do not use that address.',
 'diligent-robotics':'HOLD: provider verifies Vivian Chu at Serve Robotics. Acquisition explains the parent-company domain, but current responsibility for Moxi is unresolved. Do not treat this as a verified Diligent owner.'}
plans=[]
for cid in sorted(ids):
 old=byid[cid];c,a,p=cid.split('/');base=Path('campaigns')/c/'accounts'/a
 if a=='simscale':
  old=byid[extra[0]];c,a,p=old['id'].split('/');base=Path('campaigns')/c/'accounts'/a
 brief=json.load(open(base/'research.json'));ctx=json.loads(old['context']);prior=next(x for x in brief['stakeholders'] if x['id']==p)
 owner=dict(prior);contact=json.load(open(base/p/'contact.json'));schedule=json.load(open(base/p/'schedule.json'))
 if a in new:
  r=new[a];v=r['person'];p=slug(v['name']);fid=a+'-human-owner-20260916'
  owner={'id':p,'name':v['name'],'role':v['title'],'rank':1,'seniority':'technical_owner','department':'engineering','reason':reasons[a]+' Budget and signing authority unconfirmed.','fact_ids':[fid],'apollo_id':v['id']}
  brief['facts'].append({'id':fid,'entity_id':p,'text':v['name']+' is reported by Apollo as '+v['title']+' at '+brief['company']['name']+'.','evidence':[{'source_id':r['source_id'],'quote':v['title']}]})
  prior['rank']=2;prior['reason']='Superseded unsent contact, retain for history. Current primary '+v['name']+'.'
  brief['stakeholders']=[owner,prior];contact=normalize_contact(v,owner,r['domain'],r['source_id'],r['observed_at'])
  zones={'marinelabs':'America/Vancouver','scanifly':'America/New_York','uncountable':'America/Los_Angeles'}
  schedule.update(timezone=zones[a],timezone_source='apollo_person_location',source_id=r['source_id'],location=v.get('formatted_address') or ', '.join(v[k] for k in ('city','state','country') if v.get(k)),assumed_office_location=False)
  write_json(base/p/'contact.json',contact)
 if a=='simscale':
  srcbase=Path('campaigns/contract-2026-09-17');other=json.load(open(srcbase/'accounts/simscale/research.json'));fact=next(f for f in other['facts'] if f['id']=='simscale-work');fact=dict(fact);fact['id']='simscale-workflows-work'
  ss=read_sources(srcbase)
  for e in fact['evidence']:add_source(Path('campaigns')/c,ss[e['source_id']])
  brief['facts']=[f for f in brief['facts'] if f['id']!=fact['id']]+[fact]
 workids=[f['id'] for f in brief['facts'] if f['id'].endswith('-work') or f['id']=='earthmover-existing-fault-injection']
 if a=='simscale':workids=['simscale-workflows-work']
 angle=brief['hypotheses'][0]['statement'];angle=angle.replace('Ask about overdue event-state tests.','').replace('implement one agreed recovery change','test an agreed recovery change')
 if a=='simscale':angle='Compare recovery after interruption in one agreed cloud simulation workflow, checking which valid outputs can be reused.'
 brief['recommended_motion'].update(stage='technical_contract',ask='Explain why this work caught Andrew\'s attention, connect it to his existing work and genuine motivation, then ask about a small contract project with one tentative idea and deference to actual team priorities.')
 brief['message_strategy'].update(central_reason=angle,problem_altitude='Technical interest and a practical, tentative project at the recipient\'s level. Preserve the human progression of thought; no mandatory paid/backlog/timed CTA.',expose_facts=workids,why_now=None,why_now_basis=[])
 brief['message_strategy']['do_not_claim']=['Observed problem, missing tests or available budget','Confirmed private code/data access or deployment permission','Prior relationship unless evidenced','Guaranteed outcome or response probability','Resume attached','Fixed dates, price, hours or duration']
 brief['qualification']['basis']=list(dict.fromkeys(brief['qualification'].get('basis',[])+owner['fact_ids']))
 validate_brief(brief,read_sources(Path('campaigns')/c));write_json(base/'research.json',brief);write_json(base/'contacts.json',brief['stakeholders'])
 reason=reasons.get(a,owner.get('reason','Retain researched technical recipient.'))
 packet={'phase':'research_and_strategy_complete_before_writer','completed_at':at,'company':brief['company'],'recipient':owner,'facts':brief['facts'],'hypothesis':angle,'reason_for_recipient':reason,'style_authority':'Latest Andrew correction: Neil/FIDO and supplied Archy/Nic; specific interest, actual skill connection, genuine motivation, small contract ask, tentative idea and natural call. No required paid/backlog/15 minutes.','unknowns':['Actual need and priority','Contract budget and approver','Permitted inputs and scope','Hours and dates'],'history':'Retain original timestamped mailbox evidence; local rewrite grants no sending authorization.','held':a=='diligent-robotics'}
 write_json(base/'human-progression-strategy-2026-09-16.json',packet)
 (base/'strategy.md').write_text('# '+brief['company']['name']+'\n\n'+packet['style_authority']+'\n\n'+reason+'\n\nProposed problem (hypothesis): '+angle+'\n\nBudget, access and actual need remain unknown.\n')
 plans.append({'old':old,'replaces_id':cid,'campaign':c,'account':a,'person_id':p,'contact_id':'/'.join([c,a,p]),'owner':owner,'contact':contact,'schedule':schedule,'brief':brief,'reason':reason,'held':a=='diligent-robotics','is_today':cid in {r['contact_id'] for r in today},'is_listed':cid in {r['id'] for r in listed}})
write_json(root/'human-plans.json',plans);write_json(review/'research-and-targeting.json',plans);shutil.copy2(root/'web-evidence.json',review/'web-evidence.json')
print(json.dumps({'accounts':len(plans),'new_contacts':len(new),'reuse_existing_simscale':True,'held':['diligent-robotics'],'strategy_complete_before_writing':at}))
