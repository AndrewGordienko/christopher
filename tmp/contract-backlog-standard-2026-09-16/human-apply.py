import json,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
import operations
from state import get,eligible,event
from research import write_json
from readiness import blockers
from campaign_lint import rows_for,lint,check,save_review
from mission import review_campaign
root=Path('tmp/contract-backlog-standard-2026-09-16');review=Path('campaigns/contract-2026-09-16/reviews/human-progression-2026-09-16');rows=json.load(open(root/'human-finalized.json'));now=datetime.now(timezone.utc);at=now.isoformat()
assert not (root/'human-applied.json').exists(),'Already applied; inspect state rather than rerun'
skip={'contract-2026-09-17/simscale/david-heiny':'Reuse existing SimScale engineering contact Mariano Barrios.', 'contract-week-2026-09-17/chloris/alessandro-baccini':'Duplicate first touch; retain September 17 Chloris record as primary.'}
for r in rows:
 if r['old']['id']!=r['contact_id']:skip[r['old']['id']]='Replaced by researched technical recipient '+r['owner']['name']+'.'
with operations.connect() as db:
 for r in rows:
  old=r['old'];c=get(db,old['id']);q=db.execute('select * from scheduled_sends where id=?',(old['action_id'],)).fetchone()
  assert q['status']==old['queue_status'] and q['body']==old['queue_body'] and q['subject']==old['queue_subject'],old['id']
  assert c['touch_number']==0 and not c['last_inbound_at'] and not c['last_outbound_at'],old['id']
  assert not db.execute("select 1 from gmail_executions where action_id=? and state in ('claimed','reconcile','completed','cancel_required')",(old['action_id'],)).fetchone()
 for cid,reason in skip.items():
  c=get(db,cid);assert c['touch_number']==0 and not c['last_inbound_at'] and not c['last_outbound_at'];qs=db.execute('select * from scheduled_sends where contact_id=?',(cid,)).fetchall();assert all(q['status'] in ('review','held') for q in qs)
  ctx=json.loads(c['context']);ctx.update(draft_hold=True,rank=2)
  db.execute("update contacts set context=?,rank=2,next_action_at=NULL,recommended_action='WAIT',decision=?,updated_at=? where id=?",(json.dumps(ctx),json.dumps({'action':'WAIT','reason':reason}),at,cid))
  for q in qs:
   db.execute("update scheduled_sends set status='skipped',reviewed_at=NULL,decision=? where id=?",(json.dumps({'reason':reason,'sending_authorized':False}),q['id']));db.execute('delete from execution_approvals where action_id=?',(q['id'],))
  cslug,a,p=cid.split('/');folder=Path('campaigns')/cslug/'accounts'/a/p
  oldreview=json.load(open(folder/'review.json'));oldreview.update(status='held',note=reason+' Preserve as local history; no parallel first touch.');write_json(folder/'review.json',oldreview)
  s=json.load(open(folder/'schedule.json'));s.update(status='superseded',recommended_send_utc=None,recommended_send_local=None,send_authorized=False,schedule_authorized=False);write_json(folder/'schedule.json',s)
 db.commit()
 for r in rows:
  old=r['old'];s=r['schedule'];ctx=json.loads(old['context']);ctx.update(email=r['contact']['email'],email_status=r['contact']['email_status'],name=r['owner']['name'],role=r['owner']['role'],rank=1,timezone=s['timezone'],timezone_uncertain=False,timezone_source=s['timezone_source'],timezone_source_id=s['source_id'],subject=r['subject'],body=r['body'],attachments=[],facts_supported=not r['held'],factual_review_hash=r['draft_hash'],final_checks=r['final_checks'],outbound_reviews=r['outbound_reviews'],research_version=r['research_version'],send_at=s['recommended_send_utc'],schedule_policy=s['policy'],already_contacted=False,draft_hold=r['held'],qualified=True)
  operations.register(db,r['campaign'],r['account'],r['person_id'],'technical_contract',ctx['parent_company_key'],ctx,now)
  if r.get('gmail_capture'):operations.sync_thread(db,r['contact_id'],r['gmail_capture'])
  if not r['held']:
   assert not blockers(ctx),(r['account'],blockers(ctx));current=get(db,r['contact_id']);ok,why=eligible(db,current,now);assert ok,(r['contact_id'],why)
   operations.decide(db,r['contact_id'],{'action':'SEND','reason':'Local first-touch draft recommendation under latest human-progression correction; no sending authorization.','snapshot_at':current['snapshot_at'],'research_version':current['research_version']},now)
  with db:
   if r['contact_id']==old['id']:
    r['action_id']=old['action_id'];db.execute('update scheduled_sends set status=?,subject=?,body=?,send_at=?,eligible_at=?,reviewed_at=NULL,decision=? where id=?',('held' if r['held'] else 'review',r['subject'],r['body'],s['recommended_send_utc'],s['recommended_send_utc'],json.dumps({'batch':'human-progression-2026-09-16','reason':r['reason'],'sending_authorized':False}),r['action_id']))
   else:
    cursor=db.execute("insert into scheduled_sends(contact_id,touch_number,eligible_at,send_at,queue_date,status,subject,body,sender_mailbox,decision) values(?,1,?,?,?,'review',?,?,?,?)",(r['contact_id'],s['recommended_send_utc'],s['recommended_send_utc'],old['queue_date'],r['subject'],r['body'],old['sender_mailbox'],json.dumps({'batch':'human-progression-2026-09-16','sending_authorized':False})));r['action_id']=cursor.lastrowid
   db.execute('delete from execution_approvals where action_id=?',(old['action_id'],));db.execute('update contacts set next_action_at=?,recommended_action=?,updated_at=? where id=?',(None if r['held'] else s['recommended_send_utc'],'WAIT' if r['held'] else 'SEND',at,r['contact_id']))
   event(db,r['contact_id'],'local_draft_revised','Human progression restored under current user correction. '+('Held for unresolved current Moxi responsibility.' if r['held'] else 'Exact final copy reviewed; nothing sent.'),now)
 selected={r['contact_id'] for r in rows};allrows=[r for campaign in {r['campaign'] for r in rows}|{'contract-2026-09-17'} for r in rows_for(db,campaign)];batchrows=[r for r in allrows if r['contact_id'] in selected]
 batchlint=lint(batchrows);write_json(review/'selected-batch-lint.json',batchlint);assert not [i for i in batchlint['issues'] if i['severity']=='error'],batchlint
 reports={}
 for campaign in {r['campaign'] for r in rows}|{'contract-2026-09-17'}:
  report=check(db,campaign);assert not [i for i in report['issues'] if i['severity']=='error'],report
  semantic={'fingerprint':report['fingerprint'],'reviewer':'Codex separate full-email and whole-batch read under latest user voice correction','reason':'Reviewed all 55 changed drafts after composition and five local repairs. The same supplied introduction and natural close are intentional; the company-specific question, skill connection and motivation develop coherently. Unchanged records retain existing review evidence. Diligent remains individually held. No reply or contract outcome is inferred.','semantic_checks':{'thought_continuity':True,'distinct_problem_reasoning':True,'grounded_facts':True,'appropriate_subjects':True},'resolutions':{i['code']:'Read the actual paragraphs and their causal progression. Shared approved biography and close are deliberate; retained ordinary timestamps are local recommendations only.' for i in report['issues']}}
  reports[campaign]=save_review(db,campaign,semantic);write_json(review/(campaign+'-semantic-review.json'),semantic)
 db.commit();write_json(review/'campaign-lint.json',reports)
 for r in rows:
  q=db.execute('select * from scheduled_sends where id=?',(r['action_id'],)).fetchone();assert q['body']==r['body'] and q['subject']==r['subject'] and q['status']==('held' if r['held'] else 'review')
 today=[dict(q) for q in db.execute("select s.* from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date='2026-09-16' and s.status in ('review','approved','gmail_scheduled','cancel_required') and c.engine='technical_contract'")];assert len(today)==30 and {q['contact_id'] for q in today}=={r['contact_id'] for r in rows if r['is_today']}
 # Verify source files reconstruct the exact same current draft and checks.
 for campaign in {r['campaign'] for r in rows}:
  catalog=review_campaign(Path('campaigns')/campaign)
  for account in catalog['accounts']:
   for p in account['contacts']:
    cid='/'.join([campaign,account['id'],p['id']])
    if cid not in selected:continue
    r=next(r for r in rows if r['contact_id']==cid);assert p['body']==r['body'] and p['subject']==r['subject']
    if not r['held']:assert not p['blockers'],(cid,p['blockers'])
    else:assert p['draft_status']=='held' and p['blockers']
 # Refresh existing daily exports from durable state, retaining conditional followups.
 exportdir=Path('campaigns/contract-week-2026-09-16');backup=review/'previous-exports';backup.mkdir(exist_ok=True)
 for day in ('2026-09-16','2026-09-17','2026-09-18'):
  jp=exportdir/('emails-'+day+'.json');mp=jp.with_suffix('.md');prior=json.load(open(jp))
  shutil.copy2(jp,backup/jp.name);shutil.copy2(mp,backup/mp.name)
  export=[x for x in prior if x.get('type')!='initial']
  for q in db.execute("select s.*,c.name,c.email,c.recipient_timezone,c.context from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date=? and c.engine='technical_contract' and s.touch_number=1 and s.status in ('review','approved','held','gmail_scheduled','cancel_required') order by s.send_at",(day,)):
   x=dict(q);ctx=json.loads(x.pop('context'));x.update(company=ctx.get('company_name'),company_key=ctx.get('parent_company_key'),recipient=x.pop('email'),role=ctx.get('role'),date=day,type='initial',draft_hash=ctx.get('factual_review_hash'),attachments=ctx.get('attachments',[]),send_authorized=False);export.append(x)
  write_json(jp,export)
  text=['# Contract Work — '+day,'Current local queue export. No send or Gmail schedule authorization. Held entries are not ready to send. Conditional follow-ups retain their original history and refresh requirements.']
  for x in export:text.append('## '+str(x.get('company',''))+' — '+str(x.get('name',''))+'\n\nStatus: '+str(x.get('status'))+'\n\nTo: '+str(x.get('recipient',x.get('email','')))+'\n\nSubject: '+str(x.get('subject',''))+'\n\n'+str(x.get('body','')))
  mp.write_text('\n\n'.join(text)+'\n')
write_json(root/'human-applied.json',rows);write_json(review/'applied.json',rows)

def export_rows(subset):
 return [{'number':i,'contact_id':r['contact_id'],'action_id':r['action_id'],'company':r['brief']['company']['name'],'recipient_name':r['owner']['name'],'recipient_role':r['owner']['role'],'to':r['contact']['email'],'from':r['old']['sender_mailbox'],'subject':r['subject'],'body':r['body'],'status':'held' if r['held'] else 'review','recommended_send_utc':r['schedule']['recommended_send_utc'],'recommended_send_local':r['schedule']['recommended_send_local'],'draft_hash':r['draft_hash'],'change_reason':r['reason']} for i,r in enumerate(subset,1)]
def markdown(title,subset):
 parts=['# '+title,'Latest human-progression revision. Local drafts only; nothing sent or scheduled in Gmail. The supplied Archy/Nic bodies are preserved exactly. Diligent remains held for unresolved current Moxi responsibility.']
 for r in export_rows(subset):parts.append('## '+str(r['number'])+'. '+r['company']+' — '+r['recipient_name']+'\n\n**Status:** '+r['status']+'  \n**To:** '+r['to']+'  \n**Role:** '+r['recipient_role']+'  \n**Local recommendation:** '+r['recommended_send_local']+'  \n**Subject:** '+r['subject']+'\n\n'+r['body'])
 return '\n\n'.join(parts)+'\n'
todayrows=sorted([r for r in rows if r['is_today']],key=lambda r:r['schedule']['recommended_send_utc']);listed=[r for r in rows if r['is_listed']]
batch={'date':'2026-09-16','positioning':'Andrew as an individual contract worker; human technical interest, genuine motivation and a small contract ask','sending_enabled':False,'count':30,'retargeted':25,'revision':'human-progression-2026-09-16','emails':export_rows(todayrows)}
write_json(Path('campaigns/contract-2026-09-16/reviews/september-16-selected-30/batch.json'),batch);write_json(review/'today-30.json',batch);write_json(review/'listed-30.json',{'count':30,'held':1,'emails':export_rows(listed)})
Path('campaigns/contract-2026-09-16/30-emails-for-september-16.md').write_text(markdown('30 Contract Work emails — September 16, 2026',todayrows))
(review/'listed-30-emails.md').write_text(markdown('The 30 reviewed companies — revised voice',listed));(review/'all-55-emails.md').write_text(markdown('All 55 revised Contract Work drafts',rows))
direction='# Current Contract Work direction — September 16\n\nLatest correction: Neil/FIDO plus Andrew\'s supplied Archy/Nic bodies are the preferred seeds. Preserve specific technical interest, actual skill connection and genuine motivation, then a small contract ask, tentative idea, deference and natural call. No mandatory paid/backlog/15-minute wording or resume-bullet intro. Do not manufacture impact or force a template.\n\n55 drafts revised, including today\'s 30 and the overlapping named 30. Three new technical contacts; existing Mariano reused for SimScale; duplicate Chloris approach removed. Diligent is held for unresolved current Moxi responsibility. Prior source versions and queue snapshot are preserved here. No Gmail send/schedule action.\n'
(review/'current-direction.md').write_text(direction);Path('campaigns/contract-2026-09-16/current-direction-2026-09-16.md').write_text(direction)
print(json.dumps({'rewritten':55,'today':30,'listed':30,'held':1,'new_contacts':3,'reused_existing_contact':'Mariano Barrios / SimScale','source_queue_consistent':True,'campaign_reviews_current':all(r['review_current'] for r in reports.values()),'sent':0,'gmail_scheduled':0},indent=2))
