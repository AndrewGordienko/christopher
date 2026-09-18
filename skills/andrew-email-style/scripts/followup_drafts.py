"""Per-person follow-up drafts, separate from send approvals and account routing."""
import hashlib
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from state import get, company_key, company_peers, event, stamp, TERMINAL


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS followup_drafts(
      contact_id TEXT NOT NULL REFERENCES contacts(id), review_on TEXT NOT NULL,
      subject TEXT NOT NULL, body TEXT NOT NULL, thread_id TEXT NOT NULL,
      source_path TEXT NOT NULL, evidence_version TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'review', updated_at TEXT NOT NULL,
      PRIMARY KEY(contact_id,review_on))''')
    columns={r[1] for r in db.execute('PRAGMA table_info(followup_drafts)')}
    for name,default in [('reason',"''"),('lint_metadata',"'{}'")]:
        if name not in columns:db.execute(f'ALTER TABLE followup_drafts ADD COLUMN {name} TEXT NOT NULL DEFAULT {default}')
    db.execute('''CREATE TABLE IF NOT EXISTS followup_choices(
      account_key TEXT NOT NULL, review_on TEXT NOT NULL,
      primary_contact_id TEXT NOT NULL REFERENCES contacts(id), reason TEXT NOT NULL,
      updated_at TEXT NOT NULL, PRIMARY KEY(account_key,review_on))''')


def evidence(c):
    return hashlib.sha256(json.dumps([c['thread_id'],c['last_outbound_at'],
        c['last_inbound_at'],c['touch_number'],c['status']]).encode()).hexdigest()


def prepare(db, contact_id, draft, now=None):
    """Persist every requested person's draft. This never creates a send action."""
    schema(db)
    c = get(db, contact_id)
    day = date.fromisoformat(draft['review_on']).isoformat()
    if not c['touch_number'] or not c['thread_id']:
        raise ValueError('A follow-up requires observed sent history')
    if c['status'] in TERMINAL | {'REPLIED', 'OUT_OF_OFFICE'} or c['last_inbound_at']:
        raise ValueError('Resolve the response before drafting a cold follow-up')
    if draft['thread_id'] != c['thread_id'] or draft['subject'] != c['original_subject']:
        raise ValueError('Keep the original thread and subject')
    if not draft['body'].strip() or not draft['path']:
        raise ValueError('A complete draft and source artifact are required')
    from followup_lint import blockers
    issues=blockers(db,c,draft['body'],scope_evidence=draft.get('scope_evidence'))
    if issues:raise ValueError('; '.join(i['label'] for i in issues))
    at = stamp(now or datetime.now(timezone.utc))
    with db:
        db.execute('''INSERT INTO followup_drafts(contact_id,review_on,subject,body,thread_id,
          source_path,evidence_version,status,updated_at,reason,lint_metadata)
          VALUES(?,?,?,?,?,?,?,'held',?,?,?)
          ON CONFLICT(contact_id,review_on) DO UPDATE SET subject=excluded.subject,
          body=excluded.body,thread_id=excluded.thread_id,source_path=excluded.source_path,
          evidence_version=excluded.evidence_version,status='held',updated_at=excluded.updated_at,
          reason=excluded.reason,lint_metadata=excluded.lint_metadata''',
          (contact_id,day,draft['subject'],draft['body'],draft['thread_id'],draft['path'],evidence(c),at,
           draft.get('reason','Awaiting company-level contact selection'),json.dumps({'scope_evidence':draft.get('scope_evidence')})))
        event(db, contact_id, 'followup_draft_prepared', 'Complete local draft for '+day+'; no send authorization', now)


def choose_primary(db, contact_id, day, reason, now=None):
    schema(db);c=get(db,contact_id)
    d=db.execute('SELECT * FROM followup_drafts WHERE contact_id=? AND review_on=?',(contact_id,day)).fetchone()
    if not d or d['evidence_version']!=evidence(c):raise ValueError('Refresh the draft against the current thread')
    if not reason.strip():raise ValueError('Record why this person owns the technical question')
    if any(p['status'] in TERMINAL|{'REPLIED','OUT_OF_OFFICE'} or p['last_inbound_at'] for p in company_peers(db,c)):
        raise ValueError('Resolve the account response before choosing a cold follow-up')
    if db.execute('SELECT 1 FROM settings WHERE key=?',('company_pause:'+company_key(c),)).fetchone():
        raise ValueError('This company is paused')
    from followup_lint import blockers
    issues=[i for i in blockers(db,c,d['body'],day,scope_evidence=json.loads(d['lint_metadata']).get('scope_evidence')) if i['code']!='followup_primary']
    if issues:raise ValueError('; '.join(i['label'] for i in issues))
    at=stamp(now or datetime.now(timezone.utc));key=c['engine']+':'+company_key(c)
    with db:
        for peer in company_peers(db,c):
            if peer['engine']==c['engine']:
                db.execute("UPDATE followup_drafts SET status='held',updated_at=? WHERE contact_id=? AND review_on=?",(at,peer['id'],day))
        db.execute('INSERT OR REPLACE INTO followup_choices VALUES(?,?,?,?,?)',(key,day,contact_id,reason,at))
        db.execute("UPDATE followup_drafts SET status='review',reason=?,updated_at=? WHERE contact_id=? AND review_on=?",(reason,at,contact_id,day))
        review_at=stamp(datetime.fromisoformat(day).replace(hour=9,tzinfo=ZoneInfo('Europe/London')))
        db.execute("UPDATE contacts SET recommended_action='REVIEW_FOLLOWUP',next_action_at=? WHERE id=?",(review_at,contact_id))
        event(db,contact_id,'followup_primary_selected',reason,now)


def change(db, value, now=None):
    schema(db)
    if value.get('status') not in {'review', 'held'}:
        raise ValueError('Choose review or held')
    row=db.execute('SELECT * FROM followup_drafts WHERE contact_id=? AND review_on=?',
                   (value['contact_id'],value['review_on'])).fetchone()
    if not row or row['updated_at'] != value.get('version'):
        raise ValueError('This draft changed. Refresh before updating it.')
    if value['status']=='review':
        choose_primary(db,value['contact_id'],value['review_on'],value.get('reason') or 'Andrew selected this contact as the primary follow-up.',now)
        return {'status':'saved','sending_enabled':False}
    with db:
        db.execute('UPDATE followup_drafts SET status=?,updated_at=? WHERE contact_id=? AND review_on=?',
                   (value['status'],stamp(now or datetime.now(timezone.utc)),value['contact_id'],value['review_on']))
    return {'status':'saved','sending_enabled':False}


def projection(db, campaigns=None):
    schema(db)
    from followup_lint import text_findings, original_body, shared_runs, saved_rows
    repetitions=shared_runs(saved_rows(db))
    result=[]
    for row in db.execute('SELECT * FROM followup_drafts ORDER BY review_on,contact_id'):
        d=dict(row);c=get(db,d['contact_id']);ctx=json.loads(c['context']);snap=json.loads(c['snapshot'] or '{}')
        if campaigns is not None and c['campaign'] not in campaigns:continue
        peers=company_peers(db,c)
        pause_row=db.execute('SELECT value FROM settings WHERE key=?',('company_pause:'+company_key(c),)).fetchone()
        pause=json.loads(pause_row[0]) if pause_row else {}
        # Multiple user-scheduled coworkers can already exist in Gmail. Expose
        # the matching observed message while keeping the company paused.
        external_schedule=next((x for x in pause.get('external_followups',[]) if x.get('contact_id')==c['id']),None) or pause.get('external_followup')
        paused=bool(pause_row)
        paused=paused or any(p['status'] in TERMINAL|{'REPLIED','OUT_OF_OFFICE'} or p['last_inbound_at'] for p in peers)
        changed=d['evidence_version'] != evidence(c)
        choice=db.execute('SELECT * FROM followup_choices WHERE account_key=? AND review_on=?',(c['engine']+':'+company_key(c),d['review_on'])).fetchone()
        primary=bool(choice and choice['primary_contact_id']==c['id'])
        issues=text_findings(d['body'],original_body(c),json.loads(d['lint_metadata']).get('scope_evidence'))
        issues+=repetitions.get('draft:'+c['id']+':'+d['review_on'],[])
        status='held' if paused or changed or d['status']=='held' or not primary or issues else 'review'
        primary_name=get(db,choice['primary_contact_id'])['name'] if choice else None
        reason=(pause.get('reason') or 'Account has a reply, closure or pause.') if paused else 'Thread changed since this draft was prepared.' if changed else '; '.join(i['label'] for i in issues) if issues else 'Primary follow-up: '+primary_name+'. Hold this alternative.' if not primary and primary_name else 'Select one primary contact for this company.' if not primary else 'Held by you.' if d['status']=='held' else ''
        disposition='SKIP' if c['status'] in TERMINAL else 'REWRITE' if issues else 'PRIMARY FOLLOW-UP' if status=='review' else 'HOLD'
        sent=[m for m in snap.get('messages',[]) if m.get('kind')=='sent']
        result.append(dict(d,id='followup:'+c['id']+':'+d['review_on'],kind='planned_email',
          day=d['review_on'],at=None,status=status,hold_reason=reason,manual_status=d['status'],
          disposition=disposition,editorial_status='SEND' if disposition=='PRIMARY FOLLOW-UP' else disposition,
          why=d['reason'] if status=='review' else reason,primary_contact_id=choice['primary_contact_id'] if choice else None,
          primary_name=primary_name,lint_issues=issues,word_count=len(d['body'].split()),external_schedule=external_schedule,
          conditional=True,send_eligible=False,send_authorized=False,schedule_authorized=False,
          campaign=c['campaign'],account_id=c['account_id'],person_id=c['person_id'],engine=c['engine'],
          name=c['name'],email=c['email'],role=ctx.get('role'),company=ctx.get('company_name') or c['account_id'],
          account_key=c['engine']+':'+company_key(c),sender_mailbox=c['sender_mailbox'],
          recipient_timezone=c['recipient_timezone'],touch_number=c['touch_number']+1,
          first_sent_at=c['first_sent_at'],last_outbound_at=c['last_outbound_at'],snapshot_at=c['snapshot_at'],
          last_sent_subject=c['original_subject'],last_sent_body=sent[-1].get('body','') if sent else '',
          thread_url=snap.get('source') if str(snap.get('source','')).startswith('https://mail.google.com/') else None))
    for d in result:
        d['other_contacts']=[{'name':x['name'],'contact_id':x['contact_id'],'disposition':x['disposition']} for x in result
            if x['day']==d['day'] and x['account_key']==d['account_key'] and x['contact_id']!=d['contact_id']]
    return result
