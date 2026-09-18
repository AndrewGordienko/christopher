import sys,json,sqlite3,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
import operations
from state import get,eligible,event,instant
from scheduling import validate_send_time
from readiness import fingerprint,blockers
from campaign_lint import lint,rows_for,check,save_review
root=Path('tmp/contract-sept16'); rows=json.loads((root/'planned.json').read_text()); selected={r['id'] for r in rows};now=datetime.now(timezone.utc);at=now.isoformat()
capture=json.loads((root/'gmail-capture.json').read_text());capture['observed_at']=at
replacement_query='in:anywhere {beebop.ai biapower.io}'
capture['replacement_search']={'query':replacement_query,'source':'https://mail.google.com/mail/u/0/#search/'+quote(replacement_query),'result':'No exact matches'}
folder=Path('campaigns/contract-2026-09-16/reviews/september-16-selected-30');folder.mkdir(parents=True,exist_ok=True)
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
save(folder/'gmail-capture.json',capture)
with sqlite3.connect('file:.runtime/outbound.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(folder/'before.sqlite3') as dest:src.backup(dest)
(folder/'before.sqlite3').chmod(0o600)
with operations.connect() as db:
 for r in rows:
  c=get(db,r['id']);q=db.execute('select * from scheduled_sends where id=?',(r['action_id'],)).fetchone()
  assert q['status']=='review' and q['body']==r['body'] and q['subject']==r['subject'],r['id']
  assert c['touch_number']==0 and not c['last_inbound_at'] and not c['last_outbound_at']
  assert not validate_send_time(r['new_context'],r['new_schedule']['recommended_send_utc']),r['id']
  assert not blockers(r['new_context']), (r['id'],blockers(r['new_context']))
  assert not db.execute("select 1 from gmail_executions where action_id=? and state in ('claimed','reconcile','completed','cancel_required')",(r['action_id'],)).fetchone()
 deferred=[dict(q) for q in db.execute("select s.*,c.engine,c.campaign,c.account_id,c.person_id from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date='2026-09-16' and s.status in ('review','approved','gmail_scheduled','cancel_required')") if q['contact_id'] not in selected]
 assert len(deferred)==16 and all(q['status']=='review' for q in deferred)
 save(folder/'deferred-before.json',deferred)
 # Preserve prior source recommendations and mailbox captures before local changes.
 for r in rows+deferred:
  base=Path('campaigns')/r['campaign']/'accounts'/r['account_id']/r['person_id']
  backup=folder/'source-before'/r['campaign']/r['account_id']/r['person_id'];backup.mkdir(parents=True,exist_ok=True)
  for name in ('schedule.json','review.json','mailbox-check.json'):
   if (base/name).exists():shutil.copy2(base/name,backup/name)
 for r in rows:
  operations.sync_thread(db,r['id'],capture)
  c=get(db,r['id']);ok,why=eligible(db,c,now);assert ok,(r['id'],why)
  operations.decide(db,r['id'],{'action':'SEND','reason':'Andrew requested 30 personal Contract Work emails for September 16, preserving the existing emails. Selected for practical planning, recovery, simulation or scientific-software fit; local recommendation only.','snapshot_at':c['snapshot_at'],'research_version':c['research_version']},now)
 for q in deferred:
  operations.decide(db,q['contact_id'],{'action':'WAIT','next_action_at':'2026-09-17T00:00:00+01:00','reason':'Reserve September 16\'s 30-email shared capacity for Andrew\'s explicitly requested Contract Work batch. Retain this unsent draft for later review; no Gmail action.'},now)
 with db:
  for r in rows:
   ctx=r['new_context'];send_at=r['new_schedule']['recommended_send_utc']
   db.execute('update contacts set context=?,next_action_at=?,updated_at=? where id=?',(json.dumps(ctx),send_at,at,r['id']))
   db.execute("update scheduled_sends set queue_date='2026-09-16',send_at=?,eligible_at=?,status='review',reviewed_at=NULL,decision=? where id=?",(send_at,send_at,json.dumps({'batch':'september-16-selected-30','reason':'User-requested personal contract-work selection','send_authorized':False}),r['action_id']))
   db.execute('delete from execution_approvals where action_id=?',(r['action_id'],))
   event(db,r['id'],'local_batch_selected','September 16: preserve exact existing contract-work copy; refresh account history; move local recommendation only.',now)
  db.execute('insert or replace into settings values(?,?)',('calendar_capacity:technical_contract:2026-09-16','30'))
  db.execute('insert or replace into settings values(?,?)',('calendar_capacity:all:2026-09-16','30'))
  db.execute('insert or replace into settings values(?,?)',('mailbox_check:technical_contract:2026-09-16',json.dumps({'checked_at':at,'mailbox':capture['account'],'result':'No exact matches for the 30 selected companies and listed aliases. Prior additional-mailbox checks retained separately.','source':capture['source']})))
 for r in rows:
  base=Path('campaigns')/r['campaign']/'accounts'/r['account_id']/r['person_id']
  prior=json.loads((base/'mailbox-check.json').read_text())
  save(base/'mailbox-check.json',{'checked_at':at,'mailbox':capture['account'],'mailboxes_checked':[capture['account']],'source_id':capture['tool_ref'],'already_contacted':False,'account_reply_observed':False,'result':'No exact matches in the current sending-mailbox searches.','scope_limit':capture['scope_limit'],'previous_checks':prior,'must_recheck_before_send':True})
  save(base/'gmail-refresh-2026-09-16.json',capture)
  save(base/'schedule.json',r['new_schedule'])
  review=json.loads((base/'review.json').read_text());review.update(status='draft_ready',note='Selected for September 16: existing subject and body preserved; not approved, sent or scheduled in Gmail.');save(base/'review.json',review)
  save(base.parent/'today-selection-2026-09-16.json',{'selected':True,'date':'2026-09-16','contact_id':r['id'],'action_id':r['action_id'],'subject':r['subject'],'draft_hash':fingerprint(r['subject'],r['body']),'reason':'Practical contract-worker fit; current researched draft preserved; no known prior contact in captured history.','positioning':'Andrew offering his own skills for contract work. No packaged product, promised price, duration or assumed buyer budget.','send_authorized':False})
 for q in deferred:
  base=Path('campaigns')/q['campaign']/'accounts'/q['account_id']/q['person_id'];p=base/'schedule.json';s=json.loads(p.read_text());s.update(status='deferred_for_review',recommended_send_local=None,recommended_send_utc=None,next_review_date='2026-09-17',send_authorized=False,schedule_authorized=False,rationale='September 16 reserved for Andrew\'s 30 selected Contract Work emails. Draft retained for later review.');save(p,s)
 reports={}
 for campaign in sorted({r['campaign'] for r in rows}):reports[campaign]=check(db,campaign)
 batch=[r for campaign in reports for r in rows_for(db,campaign) if r['contact_id'] in selected]
 report=lint(batch);save(folder/'selected-batch-lint.json',report);save(folder/'campaign-lint.json',reports)
 assert report['count']==30 and not [x for x in report['issues'] if x['severity']=='error'],report
 current=db.execute("select count(*) from scheduled_sends s join contacts c on c.id=s.contact_id where queue_date='2026-09-16' and s.status='review' and c.engine='technical_contract'").fetchone()[0];assert current==30,current
 save(folder/'batch.json',{'date':'2026-09-16','positioning':'Personal contract worker; preserve existing emails','sending_enabled':False,'count':30,'emails':[{'number':i,'contact_id':r['id'],'action_id':r['action_id'],'company':r['new_context']['company_name'],'recipient_name':r['name'],'recipient_role':r['new_context']['role'],'to':r['email'],'from':r['sender_mailbox'],'subject':r['subject'],'body':r['body'],'recommended_send_utc':r['new_schedule']['recommended_send_utc'],'recommended_send_local':r['new_schedule']['recommended_send_local'],'draft_hash':fingerprint(r['subject'],r['body'])} for i,r in enumerate(rows,1)]})
 print(json.dumps({'selected':current,'deferred':len(deferred),'body_changes':0,'selected_batch_issues':report['issues'],'campaign_reports':reports},indent=2))
