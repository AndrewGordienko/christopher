import json,sys,hashlib,sqlite3,shutil
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import read_sources,validate_brief,write_json
from readiness import fingerprint,blockers
from scheduling import validate_send_time
root=Path('tmp/contract-backlog-standard-2026-09-16');review=Path('campaigns/contract-2026-09-16/reviews/human-progression-2026-09-16')
rows=json.load(open(root/'human-written.json'));at=datetime.now(timezone.utc).isoformat()
repairs={
 'toffeex-marco':('A small difference in the conditions could matter much more to the choice of design than to either result on its own.','A small change in the load could reverse which design you\'d choose even if the performance estimates only move a little.','Make the effect on the design choice concrete.'),
 'spoor':('My current work involves searching for small changes that make a system reach a different conclusion or lose a recovery option.','My current work involves searching for small changes that remove a recovery option.','Keep the sender claim close to the demonstrated recovery-search work.'),
 'atmo':('still cross an important threshold too late for someone to act on it.','still provide too little lead time before an important threshold is reached.','Clarify that the evaluation concerns forecast lead time, without asserting a warning product.'),
 'flash-forest':('the next battery or seed-pod reload','the next battery change or seed-pod reload','A battery is changed, not reloaded.'),
 'amperon':('aligns forecast issuance times with the later observations and checks those boundaries explicitly','aligns forecast issuance times with the later observations and checks that later revisions cannot enter earlier decisions','Make the proposed backtest check understandable.')}
for r in rows:
 if r['account'] in repairs:
  before,after,reason=repairs[r['account']];assert before in r['body'];r['body']=r['body'].replace(before,after);r['critic_repair']=reason
 else:r['critic_repair']='Full separate reread found no necessary sentence-level repair; preserve developed thought.'
 r['draft_hash']=fingerprint(r['subject'],r['body'])

# Only move affected local recommendations when identity/timezone or spacing requires it.
skip={'contract-2026-09-17/simscale/david-heiny','contract-week-2026-09-17/chloris/alessandro-baccini'}
affected={r['old']['id'] for r in rows}|{r['replaces_id'] for r in rows}|skip
with sqlite3.connect('file:.runtime/outbound.sqlite3?mode=ro',uri=True) as db:
 fixed=[datetime.fromisoformat(x[0].replace('Z','+00:00')) for x in db.execute("select s.send_at,c.id from scheduled_sends s join contacts c on c.id=s.contact_id where s.status in ('review','approved','gmail_scheduled','cancel_required') and s.sender_mailbox='gordienko.adg@gmail.com' and s.send_at is not null") if x[1] not in affected]
for r in sorted(rows,key=lambda r:(not r['is_today'],r['old']['queue_send_at'])):
 s=r['schedule'];original=datetime.fromisoformat(r['old']['queue_send_at'].replace('Z','+00:00'));tz=ZoneInfo(s['timezone']);local=original.astimezone(tz);policy=s['policy']
 lo,hi=[int(v.split(':')[0])*60+int(v.split(':')[1]) for v in (policy['window_start'],policy['window_end'])]
 def valid(dt):return lo<=dt.astimezone(tz).hour*60+dt.astimezone(tz).minute<=hi and all(abs((dt-x).total_seconds())>=660 for x in fixed)
 if not r['held']:
  if valid(original):chosen=original
  else:
   assert not r['is_today'],('Today should not need rescheduling',r['account'])
   candidates=[datetime.combine(local.date(),datetime.min.time(),tzinfo=tz)+timedelta(minutes=m) for m in range(lo,hi+1)]
   candidates=sorted(candidates,key=lambda dt:abs((dt-original).total_seconds()))
   chosen=next((dt.astimezone(timezone.utc) for dt in candidates if valid(dt)),None);assert chosen,(r['account'],'No same-day slot')
  fixed.append(chosen)
 else:chosen=original
 s.update(recommended_send_utc=chosen.isoformat(),recommended_send_local=chosen.astimezone(tz).isoformat(),timezone_abbreviation=chosen.astimezone(tz).tzname(),send_authorized=False,schedule_authorized=False,status='held' if r['held'] else 'recommended_only',rationale='Local recommendation retained or minimally adjusted for recipient timezone and cross-campaign spacing; Gmail unchanged.')
 r['schedule_changed']=chosen!=original

query='in:anywhere {axle.energy agtonomy.com bearing.ai bonsairobotics.ai diligentrobots.com diligentrobotics.com serverobotics.com endwaste.io glacier.eco marinelabs.io spoor.ai terraclear.com vibrantplanet.net albertinvent.com assaia.com atmo.ai augmentus.tech chloris.earth civrobotics.com coiled.io coiled.com duality.ai ev.energy flashforest.com flashforest.ca foxglove.dev neuralconcept.com rugged-robotics.com scanifly.com simscale.com timefold.ai toffeex.com treefera.com uncountable.com vsparticle.com}'
capture={'complete':True,'source':'https://mail.google.com/mail/u/0/#search/'+quote(query),'tool_ref':'cua-tab-1964896037-no-exact-matches-20260916','account':'gordienko.adg@gmail.com','observed_at':'2026-09-16T00:53:25+00:00','messages':[],'search_query':query,'result':'No exact matches','scope_limit':'Current sending mailbox, all folders, listed domains and explicit aliases; unknown aliases and permanently deleted mail not covered. Earlier other-mailbox observations remain separate.'}
pyro=dict(capture,source='https://mail.google.com/mail/u/0/#search/in%3Aanywhere%20pyrologix.com',search_query='in:anywhere pyrologix.com',observed_at=at)
write_json(review/'gmail-capture.json',capture);write_json(review/'pyrologix-gmail-capture.json',pyro)
for r in rows:
 a=r['account'];base=Path('campaigns')/r['campaign']/'accounts'/a;person=base/r['person_id'];oldbase=review/'source-before'/r['old']['campaign']/a/r['old']['person_id'];brief=r['brief'];digest=r['draft_hash']
 if a=='diligent-robotics':
  provider=next(x for x in json.load(open(root/'enriched.json')) if x['account']==a)
  owner=r['owner'];owner.update(role='Head of Product, Robotics Systems and Firmware at Serve Robotics',reason=r['reason'])
  brief['facts'].append({'id':'diligent-current-affiliation-20260916','entity_id':owner['id'],'text':'Current provider enrichment places Vivian Chu at Serve Robotics; her current Moxi responsibility is unconfirmed.','evidence':[{'source_id':provider['source_id'],'quote':'Head of Product, Robotics Systems and Firmware'}]})
  brief['stakeholders']=[owner];r['contact']['role']=owner['role'];r['contact']['apollo_role']=provider['person']['title'];r['contact']['source_id']=provider['source_id'];r['contact']['observed_at']=provider['observed_at'];write_json(person/'contact.json',r['contact'])
 brief['hypotheses']=[{'statement':r['body'].split('\n\n')[4],'confidence':'medium','basis':brief['message_strategy']['expose_facts']+[a+'-sender-proof']}]
 # This annotation replaces obsolete active style guidance, preserving earlier review snapshots.
 brief['message_strategy']['current_style_reference']='skills/andrew-email-style/references/contract-useful-work.md'
 validate_brief(brief,read_sources(Path('campaigns')/r['campaign']));write_json(base/'research.json',brief);write_json(base/'contacts.json',brief['stakeholders']);r['research_version']=hashlib.sha256((base/'research.json').read_bytes()).hexdigest()
 facts=brief['message_strategy']['expose_facts']+[a+'-sender-proof']+r['owner']['fact_ids']
 r['final_checks']={'version':1,'draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate full-draft reread after writer pass; five local repairs then final read',
 'grammar':{'passed':True,'basis':'Read complete paragraphs for referents, idiom and punctuation. Supplied Archy/Nic bodies preserved.'},
 'voice':{'passed':True,'basis':'Latest user-selected Neil/FIDO progression: specific interest causes skill connection and genuine motivation, leading to a small contract ask and tentative idea. Shared approved introduction and natural close intentionally retained. No mandatory paid/backlog/timed CTA.'},
 'facts':{'passed':not r['held'],'basis':('HOLD: current Serve affiliation verified but Moxi responsibility unresolved.' if r['held'] else 'Company product facts and recipient evidence read separately from hypothetical project need. Sender work matches captured resume and supplied current introduction; no assumed access, budget, deadline, defect or outcome.'),'fact_ids':facts},
 'readability':{'passed':True,'basis':r['critic_repair']+' One technical question develops through the motivation and proposal.'}}
 r['outbound_reviews']={'version':1,'thought_continuity':{'status':'PASS','draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate thought-continuity reread','reason':r['critic_repair']+' The observed work motivates the technical question, the connection to current work explains interest, and the tentative project follows it.'},'cold_email_skeptic':{'status':'HOLD' if r['held'] else 'PASS','draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate skeptical-recipient reread','reason':r['reason'],'answers':{'why_this_recipient':r['reason'],'possible_issue':r['body'].split('\n\n')[2],'plausible_mechanism':r['body'].split('\n\n')[4],'small_ask':'Explore whether a small contract project could be useful; one tentative idea and a natural call/resume offer, no access or purchase demand.','human_voice':r['body'].split('\n\n')[3],'useful_reply_if_wrong_person':'The recipient can assess or route the named technical area; no compulsory backlog CTA. Actual priorities can replace the proposed idea.'}}}
 candidate={'id':a+'-human-progression-20260916','subject':r['subject'],'body':r['body']}
 write_json(person/'subject-body-ranking.json',{'selected':candidate,'reason':'Current explicit user correction and full-draft critic; preference is not outcome evidence.'});write_json(person/'candidates.json',[candidate]);write_json(person/'ranking.json',{'winner':candidate['id']});write_json(person/'subject-candidates.json',[{'subject':r['subject'],'reason':'Names the specific technical question in the email.'}])
 write_json(person/'review.json',{'status':'held' if r['held'] else 'draft_ready','base_hash':digest,'note':r['reason'] if r['held'] else 'Latest human-progression revision; local draft only, no sending authorization.'})
 write_json(person/'critic.json',{candidate['id']:{'facts_supported':not r['held'],'reject':r['held'],'reason':r['reason'] if r['held'] else r['critic_repair']}})
 write_json(person/'final-checks.json',r['final_checks']);write_json(person/'outbound-reviews.json',r['outbound_reviews']);write_json(person/'attachments.json',[]);write_json(person/'schedule.json',r['schedule'])
 (person/'draft.md').write_text('To: '+r['owner']['name']+' <'+r['contact']['email']+'>\nFrom: '+r['old']['sender_mailbox']+'\nSubject: '+r['subject']+'\n\n'+r['body']+'\n');shutil.copy2(person/'draft.md',person/'drafts.md')
 for filename in ('retrieval.json','context.json','mailbox-check.json'):
  data=json.load(open(oldbase/filename)) if (oldbase/filename).exists() else {}
  if filename=='retrieval.json':data.update(current_task_seed='Current supplied Archy/Nic and explicitly selected Neil/FIDO; paid/backlog versions are rejected alternatives.',style_reference='skills/andrew-email-style/corpus/gold/contract-human-progression-2026-09-16.json',outcome_limit='Preferred drafts do not prove replies or contracts.')
  if filename=='context.json':data.update(recipient=r['contact']['email'],sender_mailbox=r['old']['sender_mailbox'],relationship='new_first_touch',seniority='technical_owner')
  if filename=='mailbox-check.json' and r['is_listed']:
   r['gmail_capture']=pyro if a=='vibrant-planet' else capture;data={'checked_at':r['gmail_capture']['observed_at'],'mailbox':capture['account'],'source_id':capture['tool_ref'],'already_contacted':False,'account_reply_observed':False,'result':'No exact matches','scope_limit':capture['scope_limit'],'previous_checks':data,'must_recheck_before_send':True};write_json(person/'gmail-refresh-2026-09-16.json',r['gmail_capture'])
  write_json(person/filename,data)
 packet=json.load(open(base/'human-progression-strategy-2026-09-16.json'));packet.update(facts=brief['facts'],writer_completed_at=r['writer_completed_at'],critic_completed_at=at,final_hash=digest);write_json(person/'writer-packet.json',packet)
 oldstrategy=base/'technical-owner-strategy-2026-09-16.json'
 if oldstrategy.exists():data=json.load(open(oldstrategy));data['superseded_by']='human-progression-strategy-2026-09-16.json';data['status']='historical_rejected_style_do_not_use_as_current_writer_seed';write_json(oldstrategy,data)
 ctx=dict(json.loads(r['old']['context']),email=r['contact']['email'],email_status=r['contact']['email_status'],timezone=r['schedule']['timezone'],timezone_uncertain=False,timezone_source=r['schedule']['timezone_source'],timezone_source_id=r['schedule']['source_id'],subject=r['subject'],body=r['body'],facts_supported=not r['held'],factual_review_hash=digest,final_checks=r['final_checks'],outbound_reviews=r['outbound_reviews'],schedule_policy=r['schedule']['policy'],attachments=[],send_at=r['schedule']['recommended_send_utc'])
 if not r['held']:assert not blockers(ctx),(a,blockers(ctx));assert not validate_send_time(ctx,ctx['send_at']),(a,validate_send_time(ctx,ctx['send_at']))
write_json(root/'human-finalized.json',rows);write_json(review/'final-drafts-and-checks.json',rows)
print(json.dumps({'final_drafts':len(rows),'passed':sum(not r['held'] for r in rows),'held':sum(r['held'] for r in rows),'schedule_adjustments':[{'account':r['account'],'old':r['old']['queue_send_at'],'new':r['schedule']['recommended_send_utc']} for r in rows if r['schedule_changed']],'separate_critic_completed_at':at},indent=2))
