"""Exact individual approval records and Gmail UI execution receipts. No mail API.

Codex performs Chrome interactions under references/gmail-execution.md. This CLI
validates the approved record and observed result; it never clicks or sends.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from research import WORKSPACE
from readiness import blockers

POLICY_PATH = Path(__file__).resolve().parents[1] / 'policies/mailboxes.json'

def mailbox_policy(engine):
    return json.loads(POLICY_PATH.read_text()).get(engine, {})

def labels_for(engine, company):
    from gmail_labels import ROOT,WORKSPACES,STATUSES
    return [ROOT,WORKSPACES[engine],STATUSES['Scheduled']]

def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS execution_approvals(
        action_id INTEGER PRIMARY KEY REFERENCES scheduled_sends(id),
        approval_hash TEXT NOT NULL, record TEXT NOT NULL, approved_at TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS gmail_executions(
        action_id INTEGER PRIMARY KEY REFERENCES scheduled_sends(id),
        approval_hash TEXT NOT NULL, state TEXT NOT NULL, started_at TEXT NOT NULL,
        completed_at TEXT, gmail_url TEXT, thread_id TEXT, message_id TEXT, receipt TEXT)''')

def action_record(db, action_id):
    from state import get, instant
    row = db.execute('SELECT * FROM scheduled_sends WHERE id=?', (action_id,)).fetchone()
    if not row: raise ValueError('Unknown queue action')
    c = get(db, row['contact_id']); ctx = json.loads(c['context'])
    attachments = [{k:a.get(k) for k in ('kind','filename','path','sha256','draft_hash')} for a in ctx.get('attachments',[])]
    return {'action_id':action_id, 'contact_id':c['id'], 'engine':c['engine'],
            'company':ctx.get('company_name') or c['account_id'],
            'sender_mailbox':c['sender_mailbox'], 'recipient':c['email'], 'cc':[], 'bcc':[],
            'subject':row['subject'], 'body':row['body'], 'attachments':attachments,
            'send_at':instant(row['send_at']).isoformat() if row['send_at'] else None,
            'recipient_timezone':c['recipient_timezone'], 'thread_id':row['thread_id'] if row['touch_number']>1 else None,
            'labels':labels_for(c['engine'],ctx.get('company_name') or c['account_id']),
            'action':'gmail_schedule_send'}

def digest(record):
    return hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def validate_record(db, action_id, now=None):
    from state import get, instant, eligible, company_peers
    now = now or datetime.now(timezone.utc)
    row = db.execute('SELECT * FROM scheduled_sends WHERE id=?',(action_id,)).fetchone()
    record = action_record(db,action_id); c=get(db,record['contact_id']); ctx=json.loads(c['context'])
    from campaign_lint import require_ready
    require_ready(db,c['campaign'])
    required=mailbox_policy(c['engine']).get('sender_mailbox')
    if not required or record['sender_mailbox']!=required or row['sender_mailbox']!=required:
        raise ValueError('Sender mailbox must match the confirmed workspace account')
    if not record['send_at'] or instant(record['send_at'])<=now+timedelta(minutes=1):
        raise ValueError('Approved time has passed or is too close; choose a future slot and approve again')
    issues=blockers(ctx,record['subject'],record['body'],row['touch_number'])
    if c['engine']=='technical_contract' and row['touch_number']>1:
        from followup_lint import blockers as followup_blockers,day_for
        issues+=followup_blockers(db,c,record['body'] or '',day_for(dict(row)),row['id'])
    from scheduling import validate_send_time
    issues+=validate_send_time(ctx,record['send_at'],now)
    if issues: raise ValueError('; '.join(x['label'] for x in issues))
    ok,reason=eligible(db,c,now)
    if not ok: raise ValueError(reason)
    for a in record['attachments']:
        p=Path(a.get('path') or '')
        if not p.is_file() or p.name!=a.get('filename') or hashlib.sha256(p.read_bytes()).hexdigest()!=a.get('sha256'):
            raise ValueError('Attachment path, filename or content differs from the approved file')
    return record

def approve(db, action_id, expected_hash, now=None):
    # Called only by the individual review operation, never by nightly preparation.
    schema(db)
    record=validate_record(db,action_id,now)
    if not expected_hash or digest(record)!=expected_hash:
        raise ValueError('Recipient, sender, copy, attachment or time changed; refresh and approve this email again')
    at=(now or datetime.now(timezone.utc)).isoformat()
    db.execute('INSERT OR REPLACE INTO execution_approvals VALUES(?,?,?,?)',(action_id,expected_hash,json.dumps(record),at))
    return record

def approved_record(db,action_id,now=None):
    schema(db)
    row=db.execute('SELECT status FROM scheduled_sends WHERE id=?',(action_id,)).fetchone()
    approval=db.execute('SELECT * FROM execution_approvals WHERE action_id=?',(action_id,)).fetchone()
    if not row or row['status']!='approved' or not approval:
        raise ValueError('This email has not been individually approved in a.outbound')
    record=validate_record(db,action_id,now)
    if digest(record)!=approval['approval_hash']:
        raise ValueError('The approved record changed; individual reapproval required')
    return record,dict(approval)

def list_approved(db,date=None,now=None):
    schema(db); records=[]; held=[]
    for row in db.execute("SELECT id FROM scheduled_sends WHERE status='approved' ORDER BY send_at").fetchall():
        try:
            record,approval=approved_record(db,row['id'],now)
            if date and datetime.fromisoformat(record['send_at']).astimezone(ZoneInfo('Europe/London')).date().isoformat()!=date: continue
            records.append({**record,'approval_hash':approval['approval_hash']})
        except ValueError as exc: held.append({'action_id':row['id'],'reason':str(exc)})
    return {'approved':records,'held':held,'immediate_send_allowed':False}

def claim(db,action_id,expected_hash,now=None):
    from state import get,company_key
    schema(db)
    db.execute('BEGIN IMMEDIATE')
    try:
        record,approval=approved_record(db,action_id,now)
        if approval['approval_hash']!=expected_hash: raise ValueError('Approval changed')
        if db.execute('SELECT 1 FROM gmail_executions WHERE action_id=?',(action_id,)).fetchone():
            raise ValueError('Execution already attempted; reconcile Gmail before any retry')
        # Do not compose another person at an account with an in-flight Gmail action.
        key=company_key(get(db,record['contact_id']))
        for other in db.execute("SELECT s.contact_id FROM gmail_executions e JOIN scheduled_sends s ON s.id=e.action_id WHERE e.state IN ('claimed','reconcile','cancel_required') OR s.status IN ('gmail_scheduled','cancel_required')"):
            if company_key(get(db,other['contact_id']))==key: raise ValueError('Another Gmail action exists at this company; inspect its thread first')
        db.execute("INSERT INTO gmail_executions(action_id,approval_hash,state,started_at) VALUES(?,?,'claimed',?)",(action_id,expected_hash,(now or datetime.now(timezone.utc)).isoformat()))
        db.commit();return {**record,'approval_hash':expected_hash}
    except Exception:
        db.rollback();raise

def verify_observation(record,observation,scheduled=False):
    from state import instant
    if observation.get('source','').startswith('https://mail.google.com/') is not True or not observation.get('tool_ref'):
        raise ValueError('Gmail verification needs the actual browser observation and URL')
    if not observation.get('observed_at'): raise ValueError('Observation timestamp required')
    if not isinstance(observation.get('scheduled_at'),str): raise ValueError('Observed schedule instant required')
    for key in ('sender_mailbox','recipient','subject','body','cc','bcc'):
        if observation.get(key)!=record[key]: raise ValueError('Gmail '+key+' differs from the approved record')
    from gmail_labels import MANAGED
    if set(observation.get('labels',[])) & MANAGED != set(record['labels']): raise ValueError('Workspace/status/action labels do not match')
    if observation.get('attachment_filenames')!=[a['filename'] for a in record['attachments']]:
        raise ValueError('Gmail attachment filenames do not match')
    if instant(observation.get('scheduled_at',''))!=instant(record['send_at']): raise ValueError('Gmail scheduled time differs from the approved instant')
    if record['thread_id'] and observation.get('thread_id')!=record['thread_id']:
        raise ValueError('Follow-up thread differs from the approved thread')
    if scheduled and (observation.get('folder')!='Scheduled' or not observation.get('thread_id')):
        raise ValueError('Open and verify the message in Gmail Scheduled before recording success')

def preflight(db,action_id,observation,now=None):
    record,approval=approved_record(db,action_id,now)
    attempt=db.execute('SELECT * FROM gmail_executions WHERE action_id=?',(action_id,)).fetchone()
    if not attempt or attempt['state']!='claimed' or attempt['approval_hash']!=approval['approval_hash']:
        raise ValueError('Claim this exact approved action before composing')
    age=(now or datetime.now(timezone.utc))-datetime.fromisoformat(observation['observed_at'])
    if not timedelta(0)<=age<=timedelta(minutes=5):
        raise ValueError('Refresh the Gmail compose and schedule-dialog observation')
    verify_observation(record,observation)
    return {'action_id':action_id,'schedule_click_allowed':True,'immediate_send_allowed':False}

def confirm(db,action_id,observation,now=None):
    from state import event
    preflight(db,action_id,observation,now)
    record=action_record(db,action_id);verify_observation(record,observation,scheduled=True)
    at=(now or datetime.now(timezone.utc)).isoformat()
    with db:
        db.execute("UPDATE gmail_executions SET state='scheduled',completed_at=?,gmail_url=?,thread_id=?,message_id=?,receipt=? WHERE action_id=?",(at,observation['source'],observation['thread_id'],observation.get('message_id'),json.dumps(observation),action_id))
        db.execute("UPDATE scheduled_sends SET status='gmail_scheduled',thread_id=? WHERE id=?",(observation['thread_id'],action_id))
        event(db,record['contact_id'],'gmail_scheduled',record['send_at']+' · '+observation['source'])
    return {'action_id':action_id,'status':'gmail_scheduled','sent':False,'scheduled_at':record['send_at']}

def main():
    from state import connect
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('approved');p.add_argument('--date')
    p=sub.add_parser('claim');p.add_argument('id',type=int);p.add_argument('--approval-hash',required=True)
    for name in ('preflight','confirm'):
        p=sub.add_parser(name);p.add_argument('id',type=int);p.add_argument('observation',type=Path)
    p=sub.add_parser('reconcile');p.add_argument('id',type=int);p.add_argument('--reason',required=True)
    a=parser.parse_args()
    with connect() as db:
        schema(db)
        if a.command=='approved': result=list_approved(db,a.date)
        elif a.command=='claim': result=claim(db,a.id,a.approval_hash)
        elif a.command in ('preflight','confirm'): result=globals()[a.command](db,a.id,json.loads(a.observation.read_text()))
        else:
            db.execute("UPDATE gmail_executions SET state='reconcile',receipt=? WHERE action_id=? AND state='claimed'",(json.dumps({'reason':a.reason}),a.id))
            result={'status':'reconcile','retry_allowed':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError) as exc: raise SystemExit(str(exc))
