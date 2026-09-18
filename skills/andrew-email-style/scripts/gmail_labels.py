"""Database-derived Gmail labels. Browser execution is separate from the plan."""
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo
import json
import hashlib
from pathlib import Path

def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS gmail_label_receipts(
        mailbox TEXT NOT NULL, thread_id TEXT NOT NULL, observed_at TEXT NOT NULL,
        expected_hash TEXT NOT NULL, observation TEXT NOT NULL,
        PRIMARY KEY(mailbox,thread_id))''')

def plan_thread(db,cid,observed_labels=None,now=None):
    from state import get,instant
    from research import WORKSPACE
    c=get(db,cid)
    if not c['thread_id']: raise ValueError('No observed Gmail thread to label')
    if not c['sender_mailbox']: raise ValueError('Resolve the actual thread mailbox first')
    peers=db.execute('SELECT engine FROM contacts WHERE sender_mailbox=? AND thread_id=?',(c['sender_mailbox'],c['thread_id'])).fetchall()
    if len({r['engine'] for r in peers})!=1: raise ValueError('Thread has conflicting workspace records; reconcile before labeling')
    sends=[dict(r) for r in db.execute('SELECT * FROM scheduled_sends WHERE contact_id=?',(cid,))]
    p=WORKSPACE/'campaigns'/c['campaign']/'accounts'/c['account_id']/'opportunity.json'
    opportunity=json.loads(p.read_text()) if p.is_file() else None
    plan=reconcile_plan(c,sends,observed_labels or [],opportunity,now)
    identity={'mailbox':c['sender_mailbox'],'thread_id':c['thread_id'],'desired':plan['desired']}
    return {**plan,**identity,'contact_id':cid,'expected_hash':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
            'requires_thread_refresh':not c['snapshot_at'] or (now or datetime.now(timezone.utc))-instant(c['snapshot_at'])>timedelta(hours=24)}

def pending(db,now=None):
    schema(db);now=now or datetime.now(timezone.utc);result=[];seen=set()
    for c in db.execute('SELECT id,sender_mailbox,thread_id FROM contacts WHERE thread_id IS NOT NULL'):
        key=(c['sender_mailbox'],c['thread_id'])
        if key in seen: continue
        seen.add(key)
        try:
            p=plan_thread(db,c['id'],now=now)
            receipt=db.execute('SELECT * FROM gmail_label_receipts WHERE mailbox=? AND thread_id=?',key).fetchone()
            if not receipt or receipt['expected_hash']!=p['expected_hash'] or now-datetime.fromisoformat(receipt['observed_at'])>timedelta(hours=24):result.append(p)
        except ValueError as exc:result.append({'contact_id':c['id'],'blocked':str(exc)})
    return result

def confirm(db,cid,observation,now=None):
    schema(db);now=now or datetime.now(timezone.utc)
    p=plan_thread(db,cid,observation.get('labels',[]),now)
    if p['requires_thread_refresh']: raise ValueError('Refresh the complete thread before reconciling labels')
    if any(observation.get(k)!=p[k] for k in ('mailbox','thread_id','expected_hash')):raise ValueError('Mailbox, thread or database state changed')
    if not observation.get('source','').startswith('https://mail.google.com/') or not observation.get('tool_ref'):raise ValueError('Actual Gmail URL and browser observation required')
    age=now-datetime.fromisoformat(observation['observed_at'])
    if not timedelta(0)<=age<=timedelta(minutes=5):raise ValueError('Refresh the Gmail label observation')
    if p['add'] or p['remove']:raise ValueError('Gmail labels still differ from database state')
    if not isinstance(observation.get('previous_labels'),list):raise ValueError('Capture labels before and after reconciliation')
    if (set(observation['previous_labels'])-MANAGED)-(set(observation['labels'])-MANAGED):raise ValueError('An unrelated Gmail label was removed')
    db.execute('INSERT OR REPLACE INTO gmail_label_receipts VALUES(?,?,?,?,?)',(p['mailbox'],p['thread_id'],observation['observed_at'],p['expected_hash'],json.dumps(observation)))
    return {'status':'verified','mailbox':p['mailbox'],'thread_id':p['thread_id']}

ROOT='a.outbound'
WORKSPACES={'technical_contract':ROOT+'/Contract','wapahki_facility':ROOT+'/Wapahki','outagehub_api':ROOT+'/OutageHub'}
STATUSES={v:ROOT+'/status/'+v for v in ('Scheduled','Awaiting Reply','Reply Needed','Meeting','Opportunity','Closed','Do Not Contact')}
ACTIONS={v:ROOT+'/action/'+v for v in ('Follow-up Due','Needs Review')}
MANAGED={ROOT,*WORKSPACES.values(),*STATUSES.values(),*ACTIONS.values()}

def expected_labels(contact,sends,opportunity=None,now=None):
    from state import instant
    now=now or datetime.now(timezone.utc)
    labels={ROOT,WORKSPACES[contact['engine']]}
    state=contact['status']; status=None; action=None
    if state in {'BOUNCED','UNSUBSCRIBED'} or contact.get('bounce_status')=='bounced' or contact.get('unsubscribe_status')=='unsubscribed': status='Do Not Contact'
    elif state in {'DECLINED','COMPLETE'}: status='Closed'
    elif opportunity and opportunity.get('status') in {'complete','closed','lost'}: status='Closed'
    elif opportunity and opportunity.get('status') in {'project_identified','scope_sent','signed','paid','delivering','data_access','pilot','recovery_testing','deployment','customer','api_evaluation','commercial_discussion','integration'}: status='Opportunity'
    elif contact.get('reply_type')=='meeting_confirmed': status='Meeting'
    elif contact.get('last_inbound_at') and (not contact.get('last_outbound_at') or instant(contact['last_inbound_at'])>=instant(contact['last_outbound_at'])) and contact.get('reply_type')!='out_of_office': status='Reply Needed'
    elif any(s['status']=='gmail_scheduled' for s in sends): status='Scheduled'
    elif contact.get('touch_number'): status='Awaiting Reply'
    if status: labels.add(STATUSES[status])
    if status not in {'Do Not Contact','Closed','Reply Needed','Scheduled','Meeting','Opportunity'}:
        if contact.get('next_action_at') and instant(contact['next_action_at'])<=now and contact.get('touch_number'): action='Follow-up Due'
        if any(s['status'] in {'review','needs_draft','held'} for s in sends): labels.add(ACTIONS['Needs Review'])
    if action: labels.add(ACTIONS[action])
    return sorted(labels)

def reconcile_plan(contact,sends,observed_labels,opportunity=None,now=None):
    desired=set(expected_labels(contact,sends,opportunity,now)); observed=set(observed_labels)
    return {'desired':sorted(desired),'add':sorted(desired-observed),
            'remove':sorted((observed & MANAGED)-desired),
            'preserve':sorted(observed-MANAGED),'source_of_truth':'outbound database'}

def shortcuts(mailbox,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Europe/London'))
    tomorrow=(now+timedelta(days=1)).date(); following=tomorrow+timedelta(days=1)
    queries={'Reply Needed':'label:"'+STATUSES['Reply Needed']+'"',
        'Follow-up Due':'label:"'+ACTIONS['Follow-up Due']+'"',
        'Scheduled outreach':'in:scheduled label:"'+ROOT+'"',
        'Active Opportunities':'label:"'+STATUSES['Opportunity']+'"',
        'Do Not Contact':'label:"'+STATUSES['Do Not Contact']+'"'}
    # Gmail after:/before: filter message dates, not scheduled delivery. Never pretend otherwise.
    return [{'name':name,'url':'https://mail.google.com/mail/?authuser='+quote(mailbox,safe='')+'#search/'+quote(query,safe=''),
             'note':('All scheduled outreach; use Scheduled Tomorrow in the app for exact delivery dates.' if name=='Scheduled outreach' else None)} for name,query in queries.items()]

if __name__=='__main__':
    import argparse
    from state import connect
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('pending')
    p=sub.add_parser('plan');p.add_argument('contact');p.add_argument('observation',type=Path)
    p=sub.add_parser('confirm');p.add_argument('contact');p.add_argument('observation',type=Path)
    args=parser.parse_args()
    try:
        with connect() as db:
            if args.command=='pending':result=pending(db)
            else:
                observation=json.loads(args.observation.read_text())
                result=confirm(db,args.contact,observation) if args.command=='confirm' else plan_thread(db,args.contact,observation.get('labels',[]))
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,OSError) as exc:raise SystemExit(str(exc))
