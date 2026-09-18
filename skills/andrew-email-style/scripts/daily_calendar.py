"""Evidence-backed daily agenda. A follow-up review is never a scheduled send."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from urllib.parse import urlparse
from state import instant, stamp, get, company_key, company_peers, event, cancel, TERMINAL

ZONE = 'Europe/London'
ACTIONS = {'FOLLOW_UP_SAME_PERSON', 'CONTACT_NEXT_PERSON', 'RESEARCH_CONTACT', 'LINKEDIN_REVIEW', 'WAIT', 'COMPLETE'}


def linkedin_profile(c):
    """A sourced profile to inspect, never evidence that a connection was sent."""
    profile = json.loads(c['context']).get('linkedin_profile') or {}
    url = profile.get('url', '')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc not in {'www.linkedin.com', 'linkedin.com'} or not parsed.path.startswith('/in/'):
        return None
    return profile


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS relationship_plans(
      account_key TEXT PRIMARY KEY, contact_id TEXT NOT NULL, review_on TEXT NOT NULL,
      action TEXT NOT NULL, brief TEXT NOT NULL, reason TEXT NOT NULL,
      evidence_version TEXT NOT NULL, origin TEXT NOT NULL, updated_at TEXT NOT NULL, target_contact_id TEXT)''')
    if 'target_contact_id' not in {r[1] for r in db.execute('PRAGMA table_info(relationship_plans)')}:
        db.execute('ALTER TABLE relationship_plans ADD COLUMN target_contact_id TEXT')
    if 'draft' not in {r[1] for r in db.execute('PRAGMA table_info(relationship_plans)')}:
        db.execute('ALTER TABLE relationship_plans ADD COLUMN draft TEXT')


def day_at(value, zone=ZONE):
    return instant(value).astimezone(ZoneInfo(zone)).date().isoformat()


def add_business_days(value, count):
    day = date.fromisoformat(value)
    for _ in range(count):
        day += timedelta(days=1)
        while day.weekday() > 4:
            day += timedelta(days=1)
    return day.isoformat()


def account_key(c):
    return c['engine'] + ':' + company_key(c)


def evidence_version(c):
    return hashlib.sha256(json.dumps([c['last_outbound_at'], c['last_inbound_at'], c['touch_number'], c['status']]).encode()).hexdigest()


def prepare_followup(db, contact_id, draft, now=None):
    """Save an explicitly requested future draft without a SEND decision or queue action."""
    now = instant(now or datetime.now(timezone.utc))
    sync_plans(db, now)
    c = get(db, contact_id)
    p = db.execute('SELECT * FROM relationship_plans WHERE account_key=?', (account_key(c),)).fetchone()
    if not p or p['contact_id'] != contact_id or p['action'] != 'FOLLOW_UP_SAME_PERSON' or p['target_contact_id'] not in {None, contact_id}:
        raise ValueError('The account next action must be a follow-up to this person')
    peers = company_peers(db, c)
    if any(x['status'] in TERMINAL|{'REPLIED','OUT_OF_OFFICE'} or x['last_inbound_at'] for x in peers) or db.execute('SELECT 1 FROM settings WHERE key=?', ('company_pause:'+company_key(c),)).fetchone():
        raise ValueError('Resolve the paused account before preparing a follow-up')
    if p['review_on'] < day_at(now) or draft.get('review_on') != p['review_on']:
        raise ValueError('Use the current future relationship review date')
    if not c['thread_id'] or draft.get('thread_id') != c['thread_id'] or draft.get('subject') != c['original_subject']:
        raise ValueError('A follow-up keeps the actual sent thread and subject')
    if not isinstance(draft.get('body'), str) or not draft['body'].strip() or not draft.get('path'):
        raise ValueError('Save the complete draft and its source artifact')
    if c['engine']=='technical_contract':
        from followup_lint import blockers as followup_blockers
        issues=followup_blockers(db,c,draft['body'],scope_evidence=draft.get('scope_evidence'))
        if issues:raise ValueError('; '.join(i['label'] for i in issues))
    if draft.get('send_at') and day_at(draft['send_at']) != p['review_on']:
        raise ValueError('The proposed slot must fall on the review date in the calendar')
    value = dict(draft, evidence_version=evidence_version(c), created_at=stamp(now),
                 touch_number=c['touch_number']+1, status='conditional', needs_refresh=True,
                 send_authorized=False, schedule_authorized=False)
    with db:
        db.execute('UPDATE relationship_plans SET draft=? WHERE account_key=?', (json.dumps(value), account_key(c)))
        event(db, contact_id, 'followup_draft_prepared', 'Conditional draft for '+p['review_on']+'; no SEND decision', now)
    return value


def sent_evidence(db):
    """Deduplicate Gmail IDs and matching manual reports, never two actual sends."""
    rows = db.execute('''SELECT m.*,c.campaign,c.account_id,c.person_id,c.engine,c.name,c.email,
      c.sender_mailbox,c.recipient_timezone,c.context,c.snapshot,c.original_subject
      FROM messages m JOIN contacts c ON c.id=m.contact_id
      WHERE m.kind IN ('sent','sent_reported') ORDER BY m.sent_at''').fetchall()
    found, reported, covered = {}, {}, set()
    for row in rows:
        r = dict(row)
        key = (r['sender_mailbox'].casefold(), r['email'].casefold(), r['touch_number'])
        if r['kind'] == 'sent':
            found.setdefault((key[0], r['message_id']), r)
            covered.add(key)
        else:
            reported.setdefault(key, r)
    return list(found.values()) + [r for k,r in reported.items() if k not in covered]


def latest_body(c):
    snap = json.loads(c['snapshot'] or '{}')
    messages = [m for m in snap.get('messages', []) if m.get('kind') == 'sent']
    return (messages[-1].get('body') or '') if messages else ''


def sync_plans(db, now=None):
    schema(db)
    now = instant(now or datetime.now(timezone.utc))
    groups = {}
    for row in db.execute('SELECT * FROM contacts WHERE touch_number>0'):
        c = dict(row)
        key = account_key(c)
        # An account has one relationship plan, even if several contacts/campaigns exist.
        if key not in groups or (c['last_inbound_at'] or c['last_outbound_at']) > (groups[key]['last_inbound_at'] or groups[key]['last_outbound_at']):
            groups[key] = c
    for key, c in groups.items():
        old = db.execute('SELECT * FROM relationship_plans WHERE account_key=?', (key,)).fetchone()
        version = evidence_version(c)
        if old and old['evidence_version'] == version:
            continue
        ctx = json.loads(c['context'])
        if c['status'] in TERMINAL:
            action, due = 'COMPLETE', day_at(c['last_inbound_at'] or c['last_outbound_at'])
            brief, reason = 'Sequence closed. Do not prepare cold outreach.', 'Recorded terminal state: ' + c['status']
        elif c['status'] == 'REPLIED' or c['last_inbound_at'] and c['status'] != 'OUT_OF_OFFICE':
            action, due = 'WAIT', day_at(now)
            brief, reason = 'Read the reply and decide the next step with Andrew.', 'Human reply takes priority; other contacts at this account remain paused.'
        elif c['status'] == 'OUT_OF_OFFICE':
            action, due = 'WAIT', day_at(c['next_action_at'] or now)
            brief, reason = 'Recheck the thread after the absence.', 'Out-of-office deferral; do not count it as interest.'
        else:
            zone = c['recipient_timezone'] or ZONE
            first_day = day_at(c['first_sent_at'], zone)
            due = add_business_days(first_day, {1:3, 2:7, 3:12}.get(c['touch_number'], 15))
            if c['last_outbound_at']:
                due = max(due, add_business_days(day_at(c['last_outbound_at'], zone), 3))
            action = 'FOLLOW_UP_SAME_PERSON' if c['touch_number'] < 4 else 'COMPLETE'
            brief = 'Re-read the complete thread. Clarify the original technical question or make the ask smaller; do not repeat the biography. Refresh research before proposing a new technical reason to write.'
            reason = 'Start with the existing contact. Switch only if current evidence identifies someone closer to the problem; never do both.'
        with db:
            db.execute('INSERT OR REPLACE INTO relationship_plans(account_key,contact_id,review_on,action,brief,reason,evidence_version,origin,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                       (key,c['id'],due,action,brief,reason,version,'mailbox_state',stamp(now)))
            if action != 'COMPLETE' and c['status'] not in TERMINAL:
                review_at = datetime.fromisoformat(due).replace(hour=9,tzinfo=ZoneInfo(ZONE))
                # This is a review time in Andrew's calendar, not a recipient send time.
                db.execute('UPDATE contacts SET next_action_at=?,recommended_action=? WHERE id=?',
                           (stamp(review_at), 'REVIEW_REPLY' if c['status']=='REPLIED' else 'REVIEW_SEQUENCE',c['id']))
                db.execute("UPDATE scheduled_sends SET eligible_at=? WHERE contact_id=? AND status='waiting'",(stamp(review_at),c['id']))


def change_plan(db, value, now=None):
    if value.get('operation') == 'followup_status':
        from followup_drafts import change
        return change(db, value, now)
    schema(db)
    now = instant(now or datetime.now(timezone.utc))
    if value.get('operation') == 'capacity':
        day = date.fromisoformat(value['day']).isoformat()
        engine = value['engine']
        capacity = value['capacity']
        if engine not in {'all','technical_contract','wapahki_facility','outagehub_api'} or type(capacity) is not int or not 1 <= capacity <= 200:
            raise ValueError('Choose a daily target from 1 to 200')
        with db:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('calendar_capacity:'+engine+':'+day,json.dumps(capacity)))
        return {'status':'saved'}
    plan = db.execute('SELECT * FROM relationship_plans WHERE account_key=?',(value['account_key'],)).fetchone()
    if not plan or plan['updated_at'] != value.get('version'):
        raise ValueError('The account changed. Refresh before saving its next action.')
    action = value['action']; due = date.fromisoformat(value['review_on']).isoformat()
    if action not in ACTIONS or due < day_at(now):
        raise ValueError('Choose a valid next action and a date today or later')
    c = get(db,plan['contact_id'])
    target = get(db,value.get('contact_id') or c['id'])
    if account_key(target) != account_key(c):
        raise ValueError('The next person must belong to this account and workspace')
    if action == 'CONTACT_NEXT_PERSON':
        if target['id'] == c['id'] or target['touch_number']:
            raise ValueError('Choose an uncontacted person at this account')
        if any(p['last_inbound_at'] or p['status'] in TERMINAL|{'REPLIED'} for p in company_peers(db,c)):
            raise ValueError('Resolve the reply or suppression before approaching another person')
        if not target['email'] or json.loads(target['context']).get('email_status') != 'verified':
            raise ValueError('Research and verify the alternate contact first')
    elif target['id'] != c['id'] and action != 'LINKEDIN_REVIEW':
        raise ValueError('Only a next-person decision can change the recipient')
    if action in {'FOLLOW_UP_SAME_PERSON','CONTACT_NEXT_PERSON','LINKEDIN_REVIEW'} and any(p['status'] in TERMINAL|{'REPLIED','OUT_OF_OFFICE'} or p['last_inbound_at'] for p in company_peers(db,c)):
        raise ValueError('This relationship is paused or closed; review its state first')
    brief = str(value.get('brief','')).strip(); reason = str(value.get('reason','')).strip()
    if not brief or not reason:
        raise ValueError('Record what to consider and why this is the next action')
    with db:
        local_pending=[r['id'] for r in db.execute("SELECT id FROM scheduled_sends WHERE contact_id=? AND touch_number>? AND status IN ('waiting','needs_draft','review','approved','held')",(c['id'],c['touch_number']))]
        for peer in company_peers(db,c):
            cancel(db,peer['id'],'Account next action changed by Andrew; re-review before execution')
        if action != 'COMPLETE':
            for qid in local_pending:
                db.execute("UPDATE scheduled_sends SET status='waiting',send_at=NULL,queue_date=NULL,body=NULL,reviewed_at=NULL,eligible_at=? WHERE id=?",(stamp(datetime.fromisoformat(due).replace(hour=9,tzinfo=ZoneInfo(ZONE))),qid))
        db.execute('UPDATE contacts SET decision=NULL WHERE id=?',(c['id'],))
        db.execute('UPDATE relationship_plans SET target_contact_id=?,review_on=?,action=?,brief=?,reason=?,origin=?,updated_at=?,draft=NULL WHERE account_key=?',
                   (target['id'],due,action,brief,reason,'user_action',stamp(now),plan['account_key']))
        db.execute('UPDATE contacts SET next_action_at=?,recommended_action=? WHERE id=?',
                   (None if action=='COMPLETE' else stamp(datetime.fromisoformat(due).replace(hour=9,tzinfo=ZoneInfo(ZONE))),action,c['id']))
        if action=='COMPLETE':
            db.execute("UPDATE contacts SET status='COMPLETE' WHERE id=?",(c['id'],))
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('company_pause:'+company_key(c),json.dumps({'reason':reason,'contact_id':c['id'],'source':'user_action','at':stamp(now)})))
        event(db,c['id'],'next_action_changed',json.dumps({'action':action,'target':target['id'],'review_on':due,'reason':reason}),now)
    return {'status':'saved','sending_enabled':False}


def projection(db, campaigns=None, now=None):
    now = instant(now or datetime.now(timezone.utc))
    sync_plans(db,now)
    contacts = {r['id']:dict(r) for r in db.execute('SELECT * FROM contacts')}
    entries=[]
    def base(c):
        ctx=json.loads(c['context'])
        return {'contact_id':c['id'],'campaign':c['campaign'],'account_id':c['account_id'],'person_id':c['person_id'],
          'engine':c['engine'],'company':ctx.get('company_name') or c['account_id'],'name':c['name'],'role':ctx.get('role'),
          'email':c['email'],'recipient_timezone':c['recipient_timezone'],'timezone_source':ctx.get('timezone_evidence',{}).get('timezone_source'),
          'account_key':account_key(c),'last_sent_subject':c['original_subject'],'last_sent_body':latest_body(c),
          'thread_id':c['thread_id'],'snapshot_at':c['snapshot_at']}
    for r in sent_evidence(db):
        c=contacts[r['contact_id']]; snap=json.loads(c['snapshot'] or '{}')
        m=next((m for m in snap.get('messages',[]) if m.get('id')==r['message_id']),{})
        entries.append(dict(base(c),id='sent:'+r['contact_id']+':'+r['message_id'],kind='sent',status='sent' if r['kind']=='sent' else 'reported_sent',
          day=day_at(r['sent_at']),at=r['sent_at'],touch_number=r['touch_number'],subject=m.get('subject') or snap.get('subject') or r['original_subject'],
          body=m.get('body'),accepted_example=bool(snap.get('accepted_voice_example') and 'contracts' in snap.get('gmail_labels',[])),source=snap.get('source') if r['kind']=='sent' else 'user_action',message_id=r['message_id']))
    for r in db.execute("SELECT * FROM scheduled_sends WHERE status IN ('review','approved','needs_draft','held','gmail_scheduled','cancel_required')"):
        q=dict(r); c=contacts[q['contact_id']]
        if not q['send_at'] and not q['queue_date']:continue
        entries.append(dict(base(c),id='queue:'+str(q['id']),action_id=q['id'],kind='outbound',status=q['status'],day=day_at(q['send_at']) if q['send_at'] else q['queue_date'],at=q['send_at'],touch_number=q['touch_number'],subject=q['subject'],body=q['body']))
    for r in db.execute('SELECT * FROM relationship_plans'):
        p=dict(r);c=contacts[p['contact_id']]
        if p['action']=='COMPLETE':continue
        peers=company_peers(db,c)
        paused=bool(db.execute('SELECT 1 FROM settings WHERE key=?',('company_pause:'+company_key(c),)).fetchone()) or any(x['status'] in TERMINAL|{'REPLIED','OUT_OF_OFFICE'} or x['last_inbound_at'] for x in peers)
        pending=[e for e in entries if e['account_key']==p['account_key'] and e['kind']=='outbound' and e['status']!='held']
        if pending:continue
        choices=[dict(contact_id=x['id'],name=x['name'],role=json.loads(x['context']).get('role'),rank=x['rank'],email=x['email'],recipient_timezone=x['recipient_timezone'],contacted=bool(x['touch_number']),linkedin_profile=linkedin_profile(x)) for x in peers if x['engine']==c['engine']]
        target=contacts.get(p.get('target_contact_id')) or c
        prepared=json.loads(p['draft'] or '{}')
        if paused or p['action']!='FOLLOW_UP_SAME_PERSON' or target['id']!=c['id'] or prepared.get('evidence_version')!=evidence_version(c) or prepared.get('review_on')!=p['review_on'] or prepared.get('thread_id')!=c['thread_id'] or prepared.get('subject')!=c['original_subject']:
            prepared={}
        entries.append(dict(base(c),planned_draft=prepared or None,target_contact_id=target['id'],target_name=target['name'],target_role=json.loads(target['context']).get('role'),linkedin_profile=linkedin_profile(target),id='plan:'+p['account_key'],kind='reply_review' if c['status']=='REPLIED' else 'linkedin_review' if p['action']=='LINKEDIN_REVIEW' else 'followup_review',status='paused' if paused else 'review_due',
          day=p['review_on'],at=None,touch_number=c['touch_number']+1,action=p['action'],brief=p['brief'],reason=p['reason'],version=p['updated_at'],choices=choices,
          send_eligible=False,needs_refresh=True,source='persisted_relationship_plan'))
    if campaigns is not None:entries=[e for e in entries if e['campaign'] in campaigns]
    from followup_drafts import projection as followup_projection
    followups=followup_projection(db,campaigns)
    prepared_accounts={e['account_key'] for e in followups if e['status']=='review'}
    # A complete dated draft replaces the generic account reminder, not sent history.
    entries=[e for e in entries if not (e['kind']=='followup_review' and e['account_key'] in prepared_accounts)]
    entries.extend(followups)
    capacities={k.removeprefix('calendar_capacity:'):json.loads(v) for k,v in db.execute("SELECT key,value FROM settings WHERE key LIKE 'calendar_capacity:%'")}
    checks={k.removeprefix('mailbox_check:'):json.loads(v) for k,v in db.execute("SELECT key,value FROM settings WHERE key LIKE 'mailbox_check:%'")}
    goal_row=db.execute("SELECT value FROM settings WHERE key='contract_cash_goal'").fetchone()
    draft_plans=[json.loads(r[0]) for r in db.execute("SELECT value FROM settings WHERE key LIKE 'draft_calendar_plan:%' ORDER BY key")]
    followup_batches=[json.loads(r[0]) for r in db.execute("SELECT value FROM settings WHERE key LIKE 'followup_batch:%' ORDER BY key")]
    skips=[]
    for batch in followup_batches:
        for excluded in batch.get('excluded',[]):
            c=contacts.get(excluded['contact_id'])
            if not c or c['status'] not in TERMINAL or campaigns is not None and c['campaign'] not in campaigns:continue
            skips.append(dict(base(c),id='skip:'+c['id'],day=batch['day'],status='skipped',disposition='SKIP',
              editorial_status='SKIP',why='Explicit decline already answered; no further follow-up.',
              body='',subject=c['original_subject'],word_count=0,other_contacts=[],
              sender_mailbox=c['sender_mailbox'],last_outbound_at=c['last_outbound_at'],thread_url=json.loads(c['snapshot'] or '{}').get('source')))
    return {'followups':followups,'followup_skips':skips,'followup_batches':followup_batches,'draft_plans':draft_plans,'cash_goal':json.loads(goal_row[0]) if goal_row else None,'timezone':ZONE,'today':day_at(now),'default_capacity':30,'capacities':capacities,'entries':entries,'mailbox_checks':checks,'sending_enabled':False}
