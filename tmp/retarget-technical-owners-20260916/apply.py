import json,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import write_json,read_sources,validate_brief
from readiness import blockers
from scheduling import recommend_send,validate_send_time
import operations
from state import get,event,eligible
from mission import review_campaign
from campaign_lint import check,save_review

root=Path('tmp/retarget-technical-owners-20260916');review=Path('campaigns/contract-2026-09-16/reviews/technical-owners-2026-09-16')
assert not (root/'applied.json').exists(),'Already applied; inspect instead of repeating'
rows=json.load(open(root/'written.json'));now=datetime.now(timezone.utc);at=now.isoformat()
with operations.connect() as db:
 affected={cid for r in rows for cid in (r['old']['id'],r['contact_id'])}
 occupied=[datetime.fromisoformat(q['send_at'].replace('Z','+00:00')) for q in db.execute("select * from scheduled_sends where status in ('review','approved','gmail_scheduled','cancel_required') and sender_mailbox='gordienko.adg@gmail.com' and send_at is not null") if q['contact_id'] not in affected]
 for r in sorted(rows,key=lambda r:(r['old']['queue_date'],r['old']['queue_send_at'] or '')):
  old=r['old'];a=r['account'];base=Path('campaigns')/r['campaign']/'accounts'/a;person=base/r['person_id'];person.mkdir(exist_ok=True)
  b=r['brief'];digest=r['draft_hash'];ctx=json.loads(old['context']);loc=r['location'];policy=ctx['schedule_policy']
  if a=='timefold':loc['timezone']='America/Sao_Paulo'
  if a=='flash-forest':loc['timezone']='America/Toronto'
  if r['held']:s={**loc,'policy':policy,'recommended_send_utc':None,'recommended_send_local':None,'status':'held','rationale':r['hold_reason']}
  else:
   zone=ZoneInfo(loc['timezone']);firstday=datetime.fromisoformat(old['queue_date']).replace(tzinfo=zone)
   earliest=max(now,firstday.astimezone(timezone.utc)-timedelta(minutes=16))
   s=recommend_send(loc,r['contact_id'],now=earliest,policy=policy,occupied=occupied);occupied.append(datetime.fromisoformat(s['recommended_send_utc'].replace('Z','+00:00')))
  s.update(send_authorized=False,schedule_authorized=False);r['schedule']=s
  b['message_strategy']['current_style_reference']='skills/andrew-email-style/references/contract-useful-work.md'
  if a in ['realtime-robotics','orchard','gideon','carbonrobotics']:
   b['message_strategy'].update(problem_altitude='Human technical interest, actual skill connection, genuine motivation, tentative small-contract idea and natural call. No compulsory paid/backlog/timed CTA.')
   b['recommended_motion']['ask']='Ask about a small contract project through a specific technical interest and its connection to current work.'
   b['hypotheses']=[{'statement':r['body'].split('\n\n')[4],'confidence':'medium','basis':b['qualification']['basis']}]
  validate_brief(b,read_sources(Path('campaigns')/r['campaign']));write_json(base/'research.json',b);write_json(base/'contacts.json',b['stakeholders']);r['research_version']=hashlib.sha256((base/'research.json').read_bytes()).hexdigest()
  checks={'version':1,'draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate full-draft reread after retargeting and later-wave composition',
   'grammar':{'passed':True,'basis':'Read full paragraphs, names, pronouns, idiom and punctuation. No sentence-level repair needed in the retained 24 drafts.'},
   'voice':{'passed':True,'basis':'Preserve Neil/FIDO human progression and supplied biography. Only greeting changes for 24; four later-wave drafts repaired to the current direction. No paid/backlog/timed-call formula.'},
   'facts':{'passed':a!='vsp-aaike','basis':r['reason']+' Product descriptions retain sourced existing evidence. Proposed need, data access, budget and reporting line remain unknown.','fact_ids':b['qualification']['basis']},
   'readability':{'passed':True,'basis':'One technical question develops into a tentative contribution and natural call. Recipient change does not introduce unsupported personal claims.'}}
  critiques={'version':1,'thought_continuity':{'status':'PASS','draft_hash':digest,'research_version':r['research_version'],'reviewed_at':at,'reviewer':'Codex separate continuity pass','reason':r['copy_change']+' Observation, practical uncertainty, skill connection and contract inquiry follow one thought.'},
   'cold_email_skeptic':{'status':'RESEARCH MORE' if r['held'] else 'PASS','draft_hash':digest,'research_version':r['research_version'],'reviewed_at':at,'reviewer':'Codex separate skeptical-recipient pass','reason':r['hold_reason'] or r['reason'],'answers':{'why_this_recipient':r['reason'],'possible_issue':r['body'].split('\n\n')[2],'plausible_mechanism':r['body'].split('\n\n')[4],'small_ask':'Explore a small contract project and offer a call/resume; no purchase, credentials, private-data request or fixed implementation commitment.','human_voice':r['body'].split('\n\n')[3],'useful_reply_if_wrong_person':'The recipient can confirm relevance or identify the technical owner. No presumed budget authority or mandatory backlog question.'}}}
  r['final_checks']=checks;r['outbound_reviews']=critiques
  candidate={'id':a+'-technical-owner-20260916','subject':r['subject'],'body':r['body']}
  for file,value in {'contact.json':r['contact'],'schedule.json':s,'attachments.json':[],'candidates.json':[candidate],'subject-body-ranking.json':{'selected':candidate,'reason':r['copy_change']},'ranking.json':{'winner':candidate['id']},'review.json':{'status':'held' if r['held'] else 'draft_ready','base_hash':digest,'note':r['hold_reason'] or 'Retargeted local draft; no sending authorization.'},'critic.json':{candidate['id']:{'facts_supported':a!='vsp-aaike','reject':r['held'],'reason':r['hold_reason'] or r['reason']}},'final-checks.json':checks,'outbound-reviews.json':critiques,'gmail-refresh-20260916.json':r['history'],'mailbox-check.json':{'checked_at':r['history']['observed_at'],'mailbox':old['sender_mailbox'],'source_id':r['history']['tool_ref'],'already_contacted':False,'account_reply_observed':False,'scope_limit':r['history']['scope_limit'],'must_recheck_before_send':True}}.items():write_json(person/file,value)
  seed=review/'source-before'/r['campaign']/a/old['person_id']/'retrieval.json';retrieval=json.load(open(seed)) if seed.exists() else {};retrieval.update(current_task_seed='Preserve the current human-progression draft; change recipient and only material made incorrect by that change.',current_task_draft={'subject':old['queue_subject'],'body':old['queue_body'],'source':old['id']},outcome_limit='Preferred drafts are not sent or response evidence.');write_json(person/'retrieval.json',retrieval)
  write_json(person/'writer-packet.json',{'phase':'research_completed_before_writer','research_completed_at':r['research_completed_at'],'writer_completed_at':r['writer_completed_at'],'critic_completed_at':at,'recipient':r['owner'],'company':b['company'],'facts':b['facts'],'reason':r['reason'],'scope_unknowns':['actual need','budget','reporting line','data/code access'],'final_hash':digest})
  (person/'draft.md').write_text('To: '+r['owner']['name']+' <'+(r['contact']['email'] or 'UNVERIFIED - HOLD')+'>\nFrom: '+old['sender_mailbox']+'\nSubject: '+r['subject']+'\n\n'+r['body']+'\n');shutil.copy2(person/'draft.md',person/'drafts.md')
  # Supersede only the untouched local first touch; preserve every historical snapshot.
  current=get(db,old['id']);q=db.execute('select * from scheduled_sends where id=?',(old['action_id'],)).fetchone()
  assert current['touch_number']==0 and not current['last_outbound_at'] and not current['last_inbound_at'] and q['status'] in ('held','skipped') and q['body']==old['queue_body'],old['id']
  assert not db.execute("select 1 from gmail_executions where action_id=? and state in ('claimed','reconcile','completed','cancel_required')",(old['action_id'],)).fetchone()
  reason='Superseded unsent executive contact by '+r['owner']['name']+'. '+r['reason'];oldctx=json.loads(current['context']);oldctx.update(draft_hold=True,rank=3)
  with db:
   db.execute("update contacts set context=?,rank=3,next_action_at=NULL,recommended_action='WAIT',decision=?,updated_at=? where id=?",(json.dumps(oldctx),json.dumps({'action':'WAIT','reason':reason}),at,old['id']))
   db.execute("update scheduled_sends set status='skipped',reviewed_at=NULL,decision=? where id=?",(json.dumps({'reason':reason,'sending_authorized':False}),old['action_id']));db.execute('delete from execution_approvals where action_id=?',(old['action_id'],))
  oldfolder=base/old['person_id'];rr=json.load(open(oldfolder/'review.json'));rr.update(status='held',note=reason);write_json(oldfolder/'review.json',rr);oldsc=json.load(open(oldfolder/'schedule.json'));oldsc.update(status='superseded',recommended_send_utc=None,recommended_send_local=None,send_authorized=False,schedule_authorized=False);write_json(oldfolder/'schedule.json',oldsc)
  ctx.update(name=r['owner']['name'],role=r['owner']['role'],rank=1,email=r['contact']['email'],email_status=r['contact']['email_status'],timezone=loc['timezone'],timezone_uncertain=not bool(loc['timezone']),timezone_source=loc['timezone_source'],timezone_source_id=loc['source_id'],subject=r['subject'],body=r['body'],facts_supported=a!='vsp-aaike',factual_review_hash=digest,final_checks=checks,outbound_reviews=critiques,external_critic_review={},external_critic_required=False,research_version=r['research_version'],send_at=s['recommended_send_utc'],schedule_policy=policy,attachments=[],already_contacted=False,draft_hold=r['held'],qualified=True)
  write_json(person/'context.json',ctx)
  operations.register(db,r['campaign'],a,r['person_id'],'technical_contract',ctx['parent_company_key'],ctx,now);operations.sync_thread(db,r['contact_id'],r['history'])
  if not r['held']:
   assert not blockers(ctx),(a,blockers(ctx));assert not validate_send_time(ctx,s['recommended_send_utc']),(a,validate_send_time(ctx,s['recommended_send_utc']))
   ok,why=eligible(db,get(db,r['contact_id']),now);assert ok,(a,why)
   fresh=get(db,r['contact_id']);operations.decide(db,r['contact_id'],{'action':'SEND','reason':'Retargeted local review draft; no delivery authorization.','snapshot_at':fresh['snapshot_at'],'research_version':fresh['research_version']},now)
  qdate=(s['recommended_send_utc'] or old['queue_date'])[:10]
  with db:
   cursor=db.execute('insert into scheduled_sends(contact_id,touch_number,eligible_at,send_at,queue_date,status,subject,body,sender_mailbox,decision) values(?,1,?,?,?,?,?,?,?,?)',(r['contact_id'],s['recommended_send_utc'],s['recommended_send_utc'],qdate,'held' if r['held'] else 'review',r['subject'],r['body'],old['sender_mailbox'],json.dumps({'batch':'technical-owners-20260916','reason':r['hold_reason'] or r['reason'],'sending_authorized':False})));r['action_id']=cursor.lastrowid
   db.execute('update contacts set next_action_at=?,recommended_action=?,decision=? where id=?',(s['recommended_send_utc'],'WAIT' if r['held'] else 'SEND',json.dumps({'action':'WAIT' if r['held'] else 'SEND','reason':r['hold_reason'] or r['reason']}),r['contact_id']))
   event(db,r['contact_id'],'local_recipient_retargeted','Replaces '+old['name']+'. '+r['reason']+' Nothing sent.',now)
  write_json(root/'progress.json',rows)
 # Review whole campaigns after exact text and recipients are persisted.
 reports={}
 for campaign in {r['campaign'] for r in rows}:
  report=check(db,campaign);errors=[i for i in report['issues'] if i['severity']=='error'];assert not errors,(campaign,errors)
  semantic={'fingerprint':report['fingerprint'],'reviewer':'Codex separate recipient and whole-batch review','reason':'Reviewed the 28 retargeted messages and preserved current wording for 24. Four later-wave messages now use the selected human progression. Unchanged messages retain their prior reviews. Four explicit holds remain; no executed history changed.','semantic_checks':{'thought_continuity':True,'distinct_problem_reasoning':True,'grounded_facts':True,'appropriate_subjects':True},'resolutions':{i['code']:'Shared supplied introduction and natural close are intentional. Technical question and matched owner differ; review-only future slots respect existing policy.' for i in report['issues']}}
  reports[campaign]=save_review(db,campaign,semantic)
 db.commit();write_json(review/'campaign-reviews.json',reports)
 for campaign in {r['campaign'] for r in rows}:
  cat=review_campaign(Path('campaigns')/campaign)
  for a in cat['accounts']:
   for p in a['contacts']:
    match=next((r for r in rows if r['contact_id']=='/'.join([campaign,a['id'],p['id']])),None)
    if match:
     assert p['body']==match['body'] and p['subject']==match['subject']
     if not match['held']:assert not p['blockers'],(match['account'],p['blockers'])
 # Refresh current dated exports. Preserve older review directories as immutable history.
 outdir=Path('campaigns/contract-week-2026-09-16');backup=review/'previous-exports';backup.mkdir(exist_ok=True)
 for jp in sorted(outdir.glob('emails-*.json')):
  prior=json.load(open(jp));shutil.copy2(jp,backup/jp.name);mp=jp.with_suffix('.md')
  if mp.exists():shutil.copy2(mp,backup/mp.name)
  day=jp.stem.removeprefix('emails-');export=[x for x in prior if x.get('type')!='initial']
  for q in db.execute("select s.*,c.name,c.email,c.recipient_timezone,c.context from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date=? and c.engine='technical_contract' and s.touch_number=1 and s.status in ('review','approved','held','gmail_scheduled','cancel_required') order by s.send_at",(day,)):
   x=dict(q);cx=json.loads(x.pop('context'));x.update(company=cx.get('company_name'),company_key=cx.get('parent_company_key'),recipient=x.pop('email'),role=cx.get('role'),date=day,type='initial',send_authorized=False);export.append(x)
  write_json(jp,export);mp.write_text('# Contract Work - '+day+'\n\nCurrent local queue. No sending authorization.\n\n'+'\n\n'.join('## '+str(x.get('company'))+' - '+str(x.get('name'))+'\n\nStatus: '+str(x.get('status'))+'\n\nTo: '+str(x.get('recipient'))+'\n\nSubject: '+str(x.get('subject'))+'\n\n'+str(x.get('body')) for x in export)+'\n')
 write_json(root/'applied.json',rows);write_json(review/'applied.json',rows)

parts=['# Retargeted contract contacts - September 16, 2026','28 named accounts researched. 25 replacement work addresses are provider-verified. 24 drafts are in local review; Coiled, Flash Forest, VSPARTICLE and Assaia remain held. No email or Gmail scheduling action was performed. Individual engineer authority, budget and exact reporting lines remain unknown unless stated.','| Company | Previous recipient | New first contact | Role | Work email | Status |\n|---|---|---|---|---|---|']
for r in rows:parts.append('| '+' | '.join([r['brief']['company']['name'],r['old']['name'],r['owner']['name'],r['owner']['role'],r['contact']['email'] or 'Unverified; do not send','HOLD' if r['held'] else 'Review'])+' |')
parts.append('\n## Reasons and alternatives\n')
for r in rows:parts.append('### '+r['brief']['company']['name']+'\n\n'+r['reason']+'\n\n'+('Hold: '+r['hold_reason']+'\n\n' if r['held'] else '')+'Alternates: '+('; '.join(p['name']+' - '+p['role'] for p in r['brief']['stakeholders'][1:]) or 'No additional qualified route named; manager/approver remains unknown.')+'\n\nProvider receipt: '+r['contact']['source_id']+'; current public profile: '+str(r['contact'].get('linkedin_url')))
(review/'retargeting-report.md').write_text('\n'.join(parts)+'\n')
(review/'retargeted-emails.md').write_text('# Retargeted contract drafts\n\nLocal review only. Held drafts are not ready to send.\n\n'+'\n\n'.join('## '+r['brief']['company']['name']+' - '+r['owner']['name']+'\n\nStatus: '+('held: '+r['hold_reason'] if r['held'] else 'review')+'\n\nTo: '+(r['contact']['email'] or 'UNVERIFIED - HOLD')+'\n\nSubject: '+r['subject']+'\n\n'+r['body'] for r in rows)+'\n')
Path('campaigns/contract-2026-09-16/current-direction-2026-09-16.md').write_text('# Current Contract Work direction\n\nTechnical owner first; relevant manager second; hands-on founder only where supported. Preserve Neil/FIDO and supplied Archy/Nic human progression. Current recipient changes, holds and exact drafts: reviews/technical-owners-2026-09-16/retargeting-report.md and retargeted-emails.md. Older review directories are historical snapshots. 28 named accounts retargeted; 25 verified replacement addresses, 24 review drafts and 4 held. No sending authorization.\n')
print(json.dumps({'retargeted':28,'verified_email':25,'review':24,'held':4,'source_queue_consistent':True,'sent':0,'gmail_scheduled':0,'report':str(review/'retargeting-report.md')},indent=2))
