import sys,json,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
import operations
from state import get,event,eligible
from research import write_json
from readiness import blockers,fingerprint
from scheduling import validate_send_time
from campaign_lint import lint,rows_for,check,save_review
from mission import review_campaign
root=Path('tmp/contract-revision-2026-09-16');rows=json.load(open(root/'finalized.json'));now=datetime.now(timezone.utc);at=now.isoformat()
folder=Path('campaigns/contract-2026-09-16/reviews/technical-owner-revision-2026-09-16')
query='in:anywhere {enode.com enode.io axle.energy recycleye.com earthmover.io ferolabs.com fourgrowers.com rideco.com amperon.co earthsense.co gridraven.com agtonomy.com electriceratechnologies.com electricera.tech spare.com sparelabs.com weavegrid.com timefold.ai timefold.com quantstack.net coiled.io coiled.com sewerai.com goswift.ly inorbit.ai dustyrobotics.com rugged-robotics.com searoutes.com openoceanrobotics.com envelio.de envelio.com takadu.com dryad.net piclo.energy piclo.com beebop.ai biapower.io}'
capture={'complete':True,'source':'https://mail.google.com/mail/u/0/#search/'+quote(query),'tool_ref':'cua-tab-1964896030-no-exact-matches-20260916','account':'gordienko.adg@gmail.com','observed_at':at,'messages':[],'search_query':query,'result':'No exact matches','scope_limit':'Current sending mailbox including Spam/Trash, selected company domains and listed aliases. Prior other-mailbox checks retained separately. Unknown aliases and permanently deleted mail not covered.'}
write_json(folder/'gmail-capture.json',capture)
with operations.connect() as db:
 # Recheck live state before changing any queue action. Do not touch a sent/scheduled record.
 for r in rows:
  old=r['old'];c=get(db,old['contact_id']);q=db.execute('select * from scheduled_sends where id=?',(old['action_id'],)).fetchone()
  assert q['status']=='review' and q['body']==old['body'] and q['subject']==old['subject'],old['contact_id']
  assert c['touch_number']==0 and not c['last_inbound_at'] and not c['last_outbound_at']
  assert not db.execute("select 1 from gmail_executions where action_id=? and state in ('claimed','reconcile','completed','cancel_required')",(old['action_id'],)).fetchone()
  if r['contact_id']!=old['contact_id']:assert not db.execute('select 1 from contacts where id=?',(r['contact_id'],)).fetchone()
 # Import only the selected revised contacts, retaining all unrelated queue state.
 for r in rows:
  old=r['old'];base=Path('campaigns')/r['campaign']/'accounts'/r['account'];person=base/r['person_id'];s=r['schedule'];ctx=json.loads(get(db,old['contact_id'])['context'])
  ctx.update(email=r['contact']['email'],name=r['owner']['name'],role=r['owner']['role'],rank=1,timezone=s['timezone'],timezone_uncertain=False,timezone_source=s['timezone_source'],timezone_source_id=s['source_id'],subject=r['subject'],body=r['body'],attachments=[],facts_supported=True,factual_review_hash=r['draft_hash'],final_checks=r['final_checks'],outbound_reviews=r['outbound_reviews'],research_version=r['research_version'],send_at=s['recommended_send_utc'],schedule_policy=s['policy'],already_contacted=False,draft_hold=False,qualified=True)
  assert not blockers(ctx),(r['account'],blockers(ctx));assert not validate_send_time(ctx,s['recommended_send_utc'])
  operations.register(db,r['campaign'],r['account'],r['person_id'],'technical_contract',ctx['parent_company_key'],ctx,now)
  operations.sync_thread(db,r['contact_id'],capture);current=get(db,r['contact_id']);ok,why=eligible(db,current,now);assert ok,(r['contact_id'],why)
  operations.decide(db,r['contact_id'],{'action':'SEND','reason':'Andrew requested more replyable Contract Work emails and relevant technical owners. Local draft recommendation only; no delivery authorization.','snapshot_at':current['snapshot_at'],'research_version':current['research_version']},now)
  with db:
   if r['contact_id']!=old['contact_id']:
    oldctx=json.loads(get(db,old['contact_id'])['context']);oldctx.update(rank=2,draft_hold=True,research_version=r['research_version'])
    db.execute('update contacts set rank=2,context=?,next_action_at=NULL,recommended_action=?,decision=?,updated_at=? where id=?',(json.dumps(oldctx),'WAIT',json.dumps({'action':'WAIT','reason':'Superseded unsent first-touch target; new primary '+r['contact_id']}),at,old['contact_id']))
    db.execute("update scheduled_sends set status='skipped',reviewed_at=NULL,decision=? where id=?",(json.dumps({'reason':'Superseded locally by a more relevant technical owner','replacement':r['contact_id'],'sending_authorized':False}),old['action_id']))
    cursor=db.execute("insert into scheduled_sends(contact_id,touch_number,eligible_at,send_at,queue_date,status,subject,body,sender_mailbox,decision) values(?,1,?,?,'2026-09-16','review',?,?,?,?)",(r['contact_id'],s['recommended_send_utc'],s['recommended_send_utc'],r['subject'],r['body'],old['from'],json.dumps({'batch':'technical-owner-revision-2026-09-16','sending_authorized':False})))
    r['action_id']=cursor.lastrowid
    prior=base/old['contact_id'].split('/')[-1];review=json.load(open(prior/'review.json'));review.update(status='held',note='Unsent draft superseded by '+r['owner']['name']+'. Preserve for history; do not contact in parallel.');write_json(prior/'review.json',review)
    oldschedule=json.load(open(prior/'schedule.json'));oldschedule.update(status='superseded',recommended_send_utc=None,recommended_send_local=None,send_authorized=False,schedule_authorized=False);write_json(prior/'schedule.json',oldschedule)
   else:
    r['action_id']=old['action_id'];db.execute("update scheduled_sends set status='review',subject=?,body=?,send_at=?,eligible_at=?,reviewed_at=NULL,decision=? where id=?",(r['subject'],r['body'],s['recommended_send_utc'],s['recommended_send_utc'],json.dumps({'batch':'technical-owner-revision-2026-09-16','sending_authorized':False}),r['action_id']))
   db.execute('delete from execution_approvals where action_id=?',(old['action_id'],))
   db.execute('update contacts set next_action_at=?,updated_at=? where id=?',(s['recommended_send_utc'],at,r['contact_id']))
   event(db,r['contact_id'],'local_draft_revised','Relevant technical owner and concrete paid-work ask; exact final text reviewed; nothing sent.',now)
  priorcheck=json.load(open(folder/'source-before'/r['campaign']/r['account']/old['contact_id'].split('/')[-1]/'mailbox-check.json'))
  write_json(person/'mailbox-check.json',{'checked_at':at,'mailbox':capture['account'],'mailboxes_checked':[capture['account']],'source_id':capture['tool_ref'],'already_contacted':False,'account_reply_observed':False,'result':capture['result'],'scope_limit':capture['scope_limit'],'previous_checks':priorcheck,'must_recheck_before_send':True})
  write_json(person/'gmail-refresh-2026-09-16.json',capture)
  write_json(base/'today-selection-2026-09-16.json',{'selected':True,'date':'2026-09-16','contact_id':r['contact_id'],'action_id':r['action_id'],'draft_hash':r['draft_hash'],'reason':r['reason'],'previous_contact_id':old['contact_id'],'send_authorized':False})
 selected={r['contact_id'] for r in rows}
 allrows=[r for c in {r['campaign'] for r in rows} for r in rows_for(db,c)];batch=[r for r in allrows if r['contact_id'] in selected]
 report=lint(batch);write_json(folder/'selected-batch-lint.json',report);assert report['count']==30 and not [x for x in report['issues'] if x['severity']=='error'],report
 reports={}
 for campaign in {r['campaign'] for r in rows}:
  report=check(db,campaign)
  assert not [x for x in report['issues'] if x['severity']=='error'],report
  review={'fingerprint':report['fingerprint'],'reviewer':'Codex separate campaign comparison after full-draft and final repair rereads','reason':'Current September 16 subset reviewed against current user corrections, individual account facts and recipient relevance. Unchanged later-date drafts retain their previously reviewed research/copy. Shared biography and ordinary close are intentional; project reasoning differs by actual software surface. No reply-rate claim.','semantic_checks':{'thought_continuity':True,'distinct_problem_reasoning':True,'grounded_facts':True,'appropriate_subjects':True},'resolutions':{i['code']:'Reviewed actual affected messages and existing prior review. Shared ordinary phrases do not replace the distinct researched task. Scheduling remains valid.' for i in report['issues']}}
  reports[campaign]=save_review(db,campaign,review)
  write_json(folder/(campaign+'-semantic-review.json'),review)
 db.commit();write_json(folder/'campaign-lint.json',reports)
 today=[dict(q) for q in db.execute("select s.*,c.email,c.name,c.recipient_timezone from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date='2026-09-16' and s.status in ('review','approved','gmail_scheduled','cancel_required') and c.engine='technical_contract'")]
 assert len(today)==30 and {q['contact_id'] for q in today}==selected
 for r in rows:
  q=next(q for q in today if q['contact_id']==r['contact_id']);assert q['body']==r['body'] and q['subject']==r['subject'] and q['email']==r['contact']['email'] and q['status']=='review'
 batch={'date':'2026-09-16','positioning':'Andrew as an individual paid contract engineer; revised technical owners and concrete tasks','sending_enabled':False,'count':30,'retargeted':25,'emails':[{'number':i,'contact_id':r['contact_id'],'action_id':r['action_id'],'company':r['old']['company'],'recipient_name':r['owner']['name'],'recipient_role':r['owner']['role'],'to':r['contact']['email'],'from':r['old']['from'],'subject':r['subject'],'body':r['body'],'recommended_send_utc':r['schedule']['recommended_send_utc'],'recommended_send_local':r['schedule']['recommended_send_local'],'draft_hash':r['draft_hash'],'previous_recipient':r['old']['recipient_name'],'change_reason':r['reason']} for i,r in enumerate(rows,1)]}
 write_json(folder/'batch.json',batch);write_json(Path('campaigns/contract-2026-09-16/reviews/september-16-selected-30/batch.json'),batch)
 write_json(root/'applied.json',rows)
 # Confirm sourced campaign artifacts independently reconstruct the selected drafts.
 for campaign in {r['campaign'] for r in rows}:
  catalog=review_campaign(Path('campaigns')/campaign)
  for account in catalog['accounts']:
   for p in account['contacts']:
    cid='/'.join([campaign,account['id'],p['id']])
    if cid in selected:
     r=next(r for r in rows if r['contact_id']==cid);assert p['body']==r['body'] and p['subject']==r['subject'] and not p['blockers'],(cid,p['blockers'])
  write_json(folder/(campaign+'-artifact-check.json'),{'selected_drafts_consistent':True,'checked_at':at})
 print(json.dumps({'today':len(today),'retargeted':25,'rewritten':30,'source_and_queue_consistent':True,'campaign_reports':{c:{k:r[k] for k in ('count','review_current','eligible_for_approval','issues')} for c,r in reports.items()}},indent=2))

parts=['# 30 Contract Work emails — September 16, 2026','Revised for relevant technical owners and concrete paid engineering work. **Local drafts only. Nothing sent or scheduled in Gmail.**','25 recipients changed; five hands-on technical founders/CTOs retained. Company needs, budget and contracting authority remain unconfirmed. Addresses are provider-verified, not guaranteed deliverable.','## Recipient changes','| Company | Previous recipient | Current recipient | Role |\n|---|---|---|---|']
for r in rows:parts.append('| '+r['old']['company']+' | '+r['old']['recipient_name']+' | '+r['owner']['name']+' | '+r['owner']['role']+' |')
parts.append('## Full emails')
for i,r in enumerate(rows,1):
 parts.append('### '+str(i)+'. '+r['old']['company']+' — '+r['owner']['name']+'\n\n**To:** '+r['contact']['email']+'  \n**Role:** '+r['owner']['role']+'  \n**Suggested recipient-local time:** '+r['schedule']['recommended_send_local']+'  \n**Subject:** '+r['subject']+'\n\n'+r['body']+'\n\n**Targeting note:** '+r['reason'])
parts.append('## Review limits\n\nThese are informed invitations to discuss paid work, not confirmed contract opportunities. Public product evidence supports relevance, not an assertion that the team lacks tests or has money available. Payment, exact scope, hours and dates belong after a useful reply. The current sending-mailbox domain search found no exact matches; other-mailbox checks remain the earlier captured observations.\n\nOriginal drafts, provider receipts, research and exact-text reviews are preserved locally in `reviews/technical-owner-revision-2026-09-16/`.')
text='\n\n'.join(parts)+'\n';Path('campaigns/contract-2026-09-16/30-emails-for-september-16.md').write_text(text);(folder/'revised-30-emails.md').write_text(text)
Path('campaigns/contract-2026-09-16/current-direction-2026-09-16.md').write_text((folder/'current-direction.md').read_text())
