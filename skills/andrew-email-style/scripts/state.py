"""Durable draft-only thread state, dynamic follow-ups and shared daily capacity.

This module has no mail sending API. SEND decisions mean prepare for review.
Mailbox snapshots are captured by Codex from Gmail, not inferred from silence.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import sqlite3
import re
from research import WORKSPACE
from scheduling import recommend_send

DB = WORKSPACE / '.runtime/outbound.sqlite3'
HUMAN = {'positive','routing','technical_answer','meeting_proposed','meeting_confirmed','next_step','declined','human','unknown'}
TERMINAL = {'BOUNCED','UNSUBSCRIBED','DECLINED','COMPLETE'}
PENDING = ('needs_draft','review','approved','waiting','held')
CADENCE = {2:3,3:8,4:15}


def instant(value):
    dt = datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if not isinstance(dt,datetime) or dt.tzinfo is None:
        raise ValueError('Use an explicit timezone for thread and scheduling timestamps')
    return dt.astimezone(timezone.utc)


def stamp(value=None):
    return instant(value or datetime.now(timezone.utc)).isoformat()


def connect(path=DB):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=20); db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS contacts(
      id TEXT PRIMARY KEY, campaign TEXT NOT NULL, account_id TEXT NOT NULL, person_id TEXT NOT NULL,
      engine TEXT NOT NULL, entity_key TEXT NOT NULL, email TEXT, name TEXT, rank INTEGER,
      sender_mailbox TEXT, recipient_timezone TEXT, thread_id TEXT, original_subject TEXT,
      status TEXT NOT NULL DEFAULT 'RESEARCHED', touch_number INTEGER NOT NULL DEFAULT 0,
      first_sent_at TEXT, last_outbound_at TEXT, last_inbound_at TEXT, next_action_at TEXT,
      reply_type TEXT, bounce_status TEXT, unsubscribe_status TEXT, recommended_action TEXT,
      research_version TEXT, draft_version TEXT, context TEXT NOT NULL, snapshot TEXT,
      snapshot_at TEXT, decision TEXT, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS scheduled_sends(
      id INTEGER PRIMARY KEY, contact_id TEXT NOT NULL REFERENCES contacts(id), touch_number INTEGER NOT NULL,
      eligible_at TEXT, send_at TEXT, queue_date TEXT, status TEXT NOT NULL, subject TEXT, body TEXT,
      sender_mailbox TEXT, thread_id TEXT, decision TEXT, reviewed_at TEXT,
      UNIQUE(contact_id,touch_number));
    CREATE TABLE IF NOT EXISTS messages(
      contact_id TEXT NOT NULL REFERENCES contacts(id), message_id TEXT NOT NULL,
      kind TEXT NOT NULL, sent_at TEXT NOT NULL, touch_number INTEGER, outcome TEXT,
      PRIMARY KEY(contact_id,message_id));
    CREATE TABLE IF NOT EXISTS activities(
      id INTEGER PRIMARY KEY, contact_id TEXT, at TEXT NOT NULL, type TEXT NOT NULL, detail TEXT NOT NULL,
      UNIQUE(contact_id,type,detail));
    CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    path.chmod(0o600)
    return db


def event(db,cid,kind,detail,at=None):
    db.execute('INSERT OR IGNORE INTO activities(contact_id,at,type,detail) VALUES(?,?,?,?)',(cid,stamp(at),kind,detail))


def get(db,cid):
    row=db.execute('SELECT * FROM contacts WHERE id=?',(cid,)).fetchone()
    if not row: raise ValueError('Unknown contact')
    return dict(row)


def register(db,campaign,account,person,engine,entity_key,context,now=None):
    if engine == 'wapahki_facility':
        context = dict(context, cell_qualification_required=True)
    cid='/'.join((campaign,account,person)); old=db.execute('SELECT * FROM contacts WHERE id=?',(cid,)).fetchone()
    email=context.get('email'); sender=context.get('sender_mailbox')
    if old and old['touch_number'] and (email != old['email'] or (sender and sender!=old['sender_mailbox'])):
        raise ValueError('A sent sequence keeps its recipient and sending mailbox')
    version=hashlib.sha256((context.get('subject','')+'\n'+context.get('body','')).encode()).hexdigest()
    status='READY' if context.get('qualified') and context.get('body') and context.get('email_status')=='verified' else 'RESEARCHED'
    values=(cid,campaign,account,person,engine,entity_key,email,context.get('name'),context.get('rank',1),sender,context.get('timezone'),context.get('subject'),status,context.get('research_version'),version,json.dumps(context),stamp(now))
    db.execute('''INSERT INTO contacts(id,campaign,account_id,person_id,engine,entity_key,email,name,rank,sender_mailbox,recipient_timezone,original_subject,status,research_version,draft_version,context,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
      email=excluded.email,name=excluded.name,rank=excluded.rank,recipient_timezone=excluded.recipient_timezone,
      sender_mailbox=CASE WHEN contacts.touch_number=0 THEN excluded.sender_mailbox ELSE COALESCE(contacts.sender_mailbox,excluded.sender_mailbox) END,
      original_subject=CASE WHEN contacts.touch_number=0 THEN excluded.original_subject ELSE contacts.original_subject END,
      status=CASE WHEN contacts.status IN ('RESEARCHED','READY') THEN excluded.status ELSE contacts.status END,
      context=excluded.context,research_version=excluded.research_version,draft_version=excluded.draft_version,updated_at=excluded.updated_at''',values)
    if old and old['draft_version']!=version:
        db.execute("UPDATE scheduled_sends SET status='needs_draft',body=NULL,reviewed_at=NULL WHERE contact_id=? AND touch_number=1 AND status IN ('review','approved')",(cid,))
    if old and not old['touch_number'] and old['sender_mailbox']!=sender:
        db.execute('UPDATE contacts SET snapshot=NULL,snapshot_at=NULL WHERE id=?',(cid,))
        db.execute("UPDATE scheduled_sends SET status='review',sender_mailbox=?,reviewed_at=NULL WHERE contact_id=? AND status IN ('review','approved')",(sender,cid))
    suppression=db.execute('SELECT value FROM settings WHERE key=?',('suppression:'+(email or '').casefold(),)).fetchone()
    if suppression:
        reason=json.loads(suppression['value'])['reason']
        db.execute('UPDATE contacts SET status=?,next_action_at=NULL WHERE id=?',('BOUNCED' if reason=='bounce' else 'UNSUBSCRIBED',cid))
        cancel(db,cid,'Permanent address suppression: '+reason)
    event(db,cid,'researched','Added to '+engine,now); db.commit(); return cid


def cancel(db,cid,reason):
    db.execute("UPDATE scheduled_sends SET status='skipped',decision=? WHERE contact_id=? AND status IN ('needs_draft','review','approved','waiting','held')",(reason,cid))
    db.execute("UPDATE scheduled_sends SET status='cancel_required',decision=? WHERE contact_id=? AND status='gmail_scheduled'",(reason,cid))


def company_key(contact):
    return json.loads(contact['context']).get('parent_company_key') or contact['entity_key']


def company_peers(db,contact):
    key=company_key(contact)
    return [dict(row) for row in db.execute('SELECT * FROM contacts') if company_key(dict(row))==key]


def sync_thread(db,cid,snapshot):
    c=get(db,cid)
    context=json.loads(c['context'])
    if snapshot.get('complete') is not True or not snapshot.get('source') or not snapshot.get('tool_ref'):
        raise ValueError('Sync needs a complete observed thread/search with provenance')
    if not snapshot['source'].startswith(('https://mail.google.com/','gmail:')):
        raise ValueError('Use an actual Gmail capture')
    at=instant(snapshot['observed_at'])
    if c['snapshot_at'] and at<instant(c['snapshot_at']): raise ValueError('Cannot replace a newer mailbox observation')
    if snapshot.get('account')!=c['sender_mailbox']:
        raise ValueError('Thread must be read in the selected sending mailbox')
    thread=snapshot.get('id'); messages=snapshot.get('messages',[])
    if c['thread_id'] and thread!=c['thread_id']: raise ValueError('Refresh the original thread, not a new thread with a matching subject')
    if messages and not thread: raise ValueError('Observed messages need a thread ID')
    if not messages and c['touch_number']: raise ValueError('A search miss cannot erase an existing sent thread')
    seen=set(); outgoing=[]; incoming=[]
    for m in messages:
        if not m.get('id') or m['id'] in seen: raise ValueError('Messages need unique observed IDs')
        seen.add(m['id']); sent=instant(m['sent_at'])
        if sent>at: raise ValueError('Message occurs after capture')
        if m.get('kind')=='sent':
            if m.get('sender','').casefold()!=c['sender_mailbox'].casefold() or c['email'].casefold() not in [x.casefold() for x in m.get('recipients',[])]:
                raise ValueError('Outbound message does not match sender and recipient')
            outgoing.append(m)
        elif m.get('kind')!='self' and (m.get('kind')!='automatic' or context.get('pause_on_any_reply')):
            sender=m.get('sender','').casefold()
            company_reply=context.get('pause_on_any_reply') and '@' in sender and sender.rsplit('@',1)[1] in {d.casefold() for d in context.get('company_domains',[])}
            if m.get('kind')!='bounce' and sender!=(c['email'] or '').casefold() and not company_reply:
                raise ValueError('Incoming message must match this recipient; route multi-person threads explicitly')
            incoming.append(m)
    outgoing.sort(key=lambda x:instant(x['sent_at'])); incoming.sort(key=lambda x:instant(x['sent_at']))
    # Validate the entire capture before changing durable state.
    with db:
        if outgoing:
            for number,m in enumerate(outgoing,1):
                db.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?)',(cid,m['id'],'sent',stamp(m['sent_at']),number,None))
                event(db,cid,'sent',f'Touch {number} · {m["id"]}',m['sent_at'])
                db.execute("UPDATE scheduled_sends SET status='sent' WHERE contact_id=? AND touch_number=?",(cid,number))
            last=outgoing[-1]; first=outgoing[0]; n=len(outgoing)
            local_first=instant(first['sent_at']).astimezone(ZoneInfo(c['recipient_timezone'] or 'Etc/UTC'))
            eligible=stamp((local_first+timedelta(days=CADENCE[n+1])).replace(hour=0,minute=0,second=0,microsecond=0)) if n<4 else None
            if c['status']=='OUT_OF_OFFICE' and c['next_action_at'] and eligible:
                eligible=max(eligible,c['next_action_at'])
            if c['status']=='REPLIED': eligible=c['next_action_at']
            db.execute("UPDATE contacts SET touch_number=?,first_sent_at=?,last_outbound_at=?,thread_id=?,original_subject=?,next_action_at=?,status=CASE WHEN status IN ('REPLIED','DECLINED','BOUNCED','UNSUBSCRIBED','COMPLETE','OUT_OF_OFFICE') THEN status ELSE 'AWAITING_REPLY' END WHERE id=?",
                       (n,stamp(first['sent_at']),stamp(last['sent_at']),thread,snapshot.get('subject') or c['original_subject'],eligible,cid))
            if eligible and c['status'] not in TERMINAL|{'REPLIED'}:
                db.execute("INSERT OR IGNORE INTO scheduled_sends(contact_id,touch_number,eligible_at,status,sender_mailbox,thread_id) VALUES(?,?,?,'waiting',?,?)",(cid,n+1,eligible,c['sender_mailbox'],thread))
        for m in incoming:
            kind=m.get('outcome') or m.get('kind','unknown')
            if kind not in HUMAN|{'out_of_office','bounce','unsubscribe','automatic'}: kind='unknown'
            nearest=max([i for i,o in enumerate(outgoing,1) if instant(o['sent_at'])<instant(m['sent_at'])],default=None)
            existing=db.execute('SELECT outcome FROM messages WHERE contact_id=? AND message_id=?',(cid,m['id'])).fetchone()
            db.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?)',(cid,m['id'],m.get('kind','unknown'),stamp(m['sent_at']),nearest,kind))
            if existing and existing['outcome']==kind: continue
            if existing: db.execute('UPDATE messages SET outcome=? WHERE contact_id=? AND message_id=?',(kind,cid,m['id']))
            event(db,cid,'reply',kind+' · '+m['id'],m['sent_at'])
            if json.loads(c['context']).get('pause_on_any_reply'):
                key=company_key(c)
                reason='Company paused after '+kind+' from '+m.get('sender',c['name'])
                db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',
                           ('company_pause:'+key,json.dumps({'reason':reason,'contact_id':cid,'message_id':m['id'],'at':stamp(at)})))
                for peer in company_peers(db,c):
                    cancel(db,peer['id'],reason)
            current=get(db,cid)
            if kind=='out_of_office':
                if current['status'] in TERMINAL|{'REPLIED'}: continue
                due=instant(m['return_at'])+timedelta(days=1) if m.get('return_at') else at+timedelta(days=7)
                if current['next_action_at']: due=max(due,instant(current['next_action_at']))
                db.execute("UPDATE contacts SET status='OUT_OF_OFFICE',next_action_at=?,reply_type='out_of_office',last_inbound_at=? WHERE id=?",(stamp(due),stamp(m['sent_at']),cid))
                db.execute("UPDATE scheduled_sends SET status='waiting',eligible_at=?,send_at=NULL,body=NULL,reviewed_at=NULL WHERE contact_id=? AND status IN ('waiting','needs_draft','review','approved')",(stamp(due),cid))
            elif kind!='automatic':
                if kind in HUMAN or kind=='unsubscribe':
                    for peer in company_peers(db,c):
                        cancel(db,peer['id'],'Account paused after '+kind+' from '+c['name'])
                status={'bounce':'BOUNCED','unsubscribe':'UNSUBSCRIBED'}.get(kind) or (current['status'] if current['status'] in TERMINAL else {'declined':'DECLINED'}.get(kind,'REPLIED'))
                cancel(db,cid,kind)
                db.execute('UPDATE contacts SET status=?,reply_type=?,last_inbound_at=?,next_action_at=?,recommended_action=?,bounce_status=?,unsubscribe_status=? WHERE id=?',
                    (status,kind,stamp(m['sent_at']),stamp(at) if status=='REPLIED' else None,'REVIEW_REPLY' if status=='REPLIED' else 'COMPLETE','bounced' if kind=='bounce' else current['bounce_status'],'unsubscribed' if kind=='unsubscribe' else current['unsubscribe_status'],cid))
                # Opt-outs and bounces suppress this address across workspaces.
                if kind in {'unsubscribe','bounce'}:
                    db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',('suppression:'+c['email'].casefold(),json.dumps({'reason':kind,'contact_id':cid,'message_id':m['id'],'at':stamp(at)})))
                if kind in {'unsubscribe','bounce','declined'}:
                    for row in db.execute('SELECT id FROM contacts WHERE lower(email)=lower(?)',(c['email'],)).fetchall():
                        cancel(db,row['id'],kind)
                        db.execute('UPDATE contacts SET status=?,next_action_at=NULL WHERE id=?',(status,row['id']))
        db.execute('UPDATE contacts SET snapshot=?,snapshot_at=?,updated_at=? WHERE id=?',(json.dumps(snapshot),stamp(at),stamp(at),cid))
    return get(db,cid)


def eligible(db,c,now):
    now=instant(now)
    if db.execute('SELECT 1 FROM settings WHERE key=?',('suppression:'+(c['email'] or '').casefold(),)).fetchone():return False,'Permanently suppressed email address'
    if c['status'] in TERMINAL|{'REPLIED'}: return False,'Conversation or terminal state'
    if db.execute("SELECT 1 FROM scheduled_sends WHERE contact_id=? AND status='held'",(c['id'],)).fetchone(): return False,'Held by Andrew'
    choice=json.loads(c['decision'] or '{}')
    ctx=json.loads(c['context'])
    if ctx.get('draft_hold'): return False,'Held by Andrew'
    if ctx.get('primary_only') and c['rank']!=1: return False,'Only contact #1 authorized for scheduling'
    if db.execute('SELECT 1 FROM settings WHERE key=?',('company_pause:'+company_key(c),)).fetchone(): return False,'Company paused; review the recorded reason'
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='relationship_plans'").fetchone():
        plan=db.execute('SELECT action FROM relationship_plans WHERE account_key=?',(c['engine']+':'+company_key(c),)).fetchone()
        if plan and plan['action']=='LINKEDIN_REVIEW': return False,'LinkedIn review is the account next action; choose an email action explicitly before queueing'
    if not c['snapshot_at'] or now-instant(c['snapshot_at'])>timedelta(hours=24): return False,'Refresh Gmail before queueing'
    if not c['recipient_timezone'] or not c['sender_mailbox']: return False,'Resolve recipient timezone and sender mailbox'
    if not ctx.get('qualified') or ctx.get('email_status')!='verified': return False,'Qualification / verified email required'
    if c['engine'] == 'wapahki_facility':
        from cell_qualification import qualification_blockers, review_blockers
        from readiness import fingerprint
        issues = qualification_blockers(ctx)
        if not c['touch_number']:
            issues += review_blockers(ctx, fingerprint(ctx.get('subject', ''), ctx.get('body', '')))
        if issues: return False, '; '.join(i['label'] for i in issues)
    # A response at any person in this account pauses the automatic sequence.
    peers=company_peers(db,c)
    if any(p['status'] in {'REPLIED','DECLINED','UNSUBSCRIBED'} for p in peers): return False,'Account conversation needs attention'
    if c['touch_number']:
        if c['touch_number']>=4: return False,'Sequence finished; new reason needed to recycle later'
        return bool(c['next_action_at']) and instant(c['next_action_at'])<=now+timedelta(days=1),'Follow-up eligibility'
    if c['rank']>1:
        if choice.get('account_choice')!=c['id'] or choice.get('snapshot_at')!=c['snapshot_at'] or not choice.get('reason'): return False,'Choose follow-up OR next contact after reviewing the account'
        previous=next((p for p in peers if p['campaign']==c['campaign'] and p['rank']==c['rank']-1),None)
        if not previous or not previous['first_sent_at']: return False,'Backup held until preceding contact is sent'
        due=instant(previous['first_sent_at']); n=0
        while n<3:
            due+=timedelta(days=1); n+=due.weekday()<5
        if now<due or not previous['snapshot_at'] or instant(previous['snapshot_at'])<due: return False,'Backup needs three business days and a refreshed thread'
    return True,'Eligible first touch'


def decide(db,cid,value,now=None):
    c=get(db,cid); now=instant(now or datetime.now(timezone.utc)); action=value.get('action')
    if action not in {'SEND','WAIT','COMPLETE'} or not value.get('reason'): raise ValueError('Decision requires SEND / WAIT / COMPLETE and a reason')
    if action=='SEND':
        ok,why=eligible(db,c,now)
        if not ok: raise ValueError(why)
        if value.get('snapshot_at')!=c['snapshot_at'] or value.get('research_version')!=c['research_version']:
            raise ValueError('Decision must use the current full thread and research version')
        if c['touch_number']:
            if not (value.get('new_reason') or c['engine']=='technical_contract' and value.get('followup_level')=='bump') or value.get('critic_passed') is not True: raise ValueError('Follow-ups need a relevant reason or explicit simple-bump choice and critic pass')
            if not value.get('research_checked_at') or now-instant(value['research_checked_at'])>timedelta(hours=24): raise ValueError('Refresh research before a follow-up')
            if c['touch_number']>=3 and value.get('still_worth_pursuing') is not True: raise ValueError('Final follow-up is optional, never automatic')
            if c['engine']=='technical_contract':
                from followup_lint import blockers as followup_blockers
                issues=followup_blockers(db,c,value.get('body') or '')
                if issues:raise ValueError('; '.join(i['label'] for i in issues))
            elif value.get('body') and re.search(r'just (?:following up|checking in)|circling back',value['body'],re.I): raise ValueError('Generic follow-up rejected')
    with db:
        db.execute('UPDATE contacts SET recommended_action=?,decision=?,updated_at=? WHERE id=?',(action,json.dumps({**value,'decided_at':stamp(now)}),stamp(now),cid))
        if action=='COMPLETE':
            cancel(db,cid,value['reason']); db.execute("UPDATE contacts SET status='COMPLETE',next_action_at=NULL WHERE id=?",(cid,))
        elif action=='WAIT':
            due=value.get('next_action_at')
            if not due or instant(due)<=now: raise ValueError('WAIT needs a future reconsideration time')
            db.execute("UPDATE scheduled_sends SET status='waiting',eligible_at=?,send_at=NULL,queue_date=NULL,body=NULL,reviewed_at=NULL WHERE contact_id=? AND status IN ('needs_draft','review','approved','waiting')",(stamp(due),cid))
            db.execute('UPDATE contacts SET next_action_at=? WHERE id=?',(stamp(due),cid))
    return get(db,cid)


def build_queue(db,day,capacity=30,now=None,queue_timezone='Europe/London'):
    from execution import schema,approved_record
    schema(db)
    now=instant(now or datetime.now(timezone.utc))
    saved_capacity=db.execute('SELECT value FROM settings WHERE key=?',('calendar_capacity:all:'+day,)).fetchone()
    if saved_capacity: capacity=json.loads(saved_capacity['value'])
    if type(capacity) is not int or not 1<=capacity<=200: raise ValueError('Daily capacity must be 1–200')
    start=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo(queue_timezone));end=start+timedelta(days=1)
    old_rows={r['contact_id']:dict(r) for r in db.execute("SELECT * FROM scheduled_sends WHERE queue_date=? AND status IN ('review','approved','needs_draft','held','gmail_scheduled','cancel_required')",(day,))}
    retained={};held=[]
    for cid,row in old_rows.items():
        if row['status'] in {'gmail_scheduled','cancel_required'}:
            retained[cid]=row;continue
        if row['status']=='approved':
            try: approved_record(db,row['id'],now);retained[cid]=row
            except ValueError as exc: held.append({'contact_id':cid,'reason':str(exc)})
    candidates=[]
    for row in db.execute('SELECT * FROM contacts'):
        c=dict(row)
        if c['id'] in retained:continue
        attempt=db.execute("SELECT 1 FROM gmail_executions e JOIN scheduled_sends s ON e.action_id=s.id WHERE s.contact_id=? AND e.state IN ('claimed','reconcile','cancel_required')",(c['id'],)).fetchone()
        if attempt:held.append({'contact_id':c['id'],'reason':'Reconcile the existing Gmail action before preparing another'});continue
        ok,why=eligible(db,c,now)
        if not ok:held.append({'contact_id':c['id'],'reason':why});continue
        ctx=json.loads(c['context']);decision=json.loads(c['decision'] or '{}')
        if c['touch_number'] and (decision.get('action')!='SEND' or decision.get('snapshot_at')!=c['snapshot_at'] or decision.get('research_version')!=c['research_version'] or now-instant(decision['decided_at'])>timedelta(hours=24)):
            held.append({'contact_id':c['id'],'reason':'Due follow-up needs fresh research and SEND / WAIT / COMPLETE decision'});continue
        if decision.get('action')=='WAIT' and c['next_action_at'] and instant(c['next_action_at'])>now:continue
        components=ctx.get('priority',{})
        scores=[max(0,min(1,float(components.get(k,0.5)))) for k in ('account_fit','recipient_fit','current_signal','relationship_value')]
        priority=sum(scores)/len(scores)*(float(decision.get('followup_value',.5)) if c['touch_number'] else 1)
        body=decision.get('body') if c['touch_number'] else ctx.get('body')
        if not body:held.append({'contact_id':c['id'],'reason':'No placeholder email'});continue
        if c['engine']=='technical_contract' and c['touch_number']:
            from followup_lint import blockers as followup_blockers
            issues=followup_blockers(db,c,body,day,old_rows.get(c['id'],{}).get('id'))
            if issues:
                held.append({'contact_id':c['id'],'reason':'; '.join(i['label'] for i in issues)});continue
        if c['engine'] == 'wapahki_facility':
            from cell_qualification import review_blockers
            from readiness import fingerprint
            # Review the selected follow-up body, which may differ from the first touch in context.
            issues = review_blockers(ctx, fingerprint(c['original_subject'] or '', body))
            if issues:
                held.append({'contact_id':c['id'],'reason':'; '.join(i['label'] for i in issues)})
                continue
        candidates.append((priority,c,body,decision))
    candidates.sort(key=lambda x:(-x[0],x[1]['rank'],x[1]['id']))
    from daily_calendar import sent_evidence
    completed=[r for r in sent_evidence(db) if start<=instant(r['sent_at'])<end]
    chosen=[];accounts={company_key(get(db,r['contact_id'])) for r in completed};addresses={r['email'].casefold() for r in completed}
    occupied=[instant(r['send_at']) for r in db.execute("SELECT send_at FROM scheduled_sends WHERE send_at IS NOT NULL AND status IN ('review','approved','gmail_scheduled','cancel_required') AND queue_date!=?",(day,))]
    for cid,row in retained.items():
        c=get(db,cid);accounts.add(company_key(c));addresses.add(c['email'].casefold());occupied.append(instant(row['send_at']))
        chosen.append({'contact_id':cid,'touch':row['touch_number'],'send_at':row['send_at'],'status':row['status'],'priority':None})
    with db:
        for cid,row in old_rows.items():
            if cid in retained or row['status']=='held':continue
            db.execute("UPDATE scheduled_sends SET status='waiting',queue_date=NULL,send_at=NULL,reviewed_at=NULL WHERE id=?",(row['id'],))
            db.execute('DELETE FROM execution_approvals WHERE action_id=?',(row['id'],))
        for priority,c,body,decision in candidates:
            if len(chosen)+len(completed)>=capacity:break
            key=company_key(c)
            if key in accounts or c['email'].casefold() in addresses:continue
            n=c['touch_number']+1
            old=db.execute('SELECT * FROM scheduled_sends WHERE contact_id=? AND touch_number=?',(c['id'],n)).fetchone()
            if old and old['status'] in {'sent','skipped','held','gmail_scheduled','cancel_required'}:continue
            earliest=max(now,start.astimezone(timezone.utc),instant(c['next_action_at']) if c['next_action_at'] else now)
            scheduled=recommend_send({'timezone':c['recipient_timezone']},c['id'],earliest,occupied=occupied)
            when=instant(scheduled['recommended_send_utc'])
            if not start<=when<end:held.append({'contact_id':c['id'],'reason':'No spaced recipient-local slot in this queue day'});continue
            db.execute("""INSERT INTO scheduled_sends(contact_id,touch_number,eligible_at,send_at,queue_date,status,subject,body,sender_mailbox,thread_id,decision)
              VALUES(?,?,?,?,?,'review',?,?,?,?,?) ON CONFLICT(contact_id,touch_number) DO UPDATE SET
              send_at=excluded.send_at,queue_date=excluded.queue_date,status='review',subject=excluded.subject,body=excluded.body,
              sender_mailbox=excluded.sender_mailbox,thread_id=excluded.thread_id,decision=excluded.decision,reviewed_at=NULL""",
              (c['id'],n,c['next_action_at'],stamp(when),day,c['original_subject'],body,c['sender_mailbox'],c['thread_id'],json.dumps(decision)))
            accounts.add(key);addresses.add(c['email'].casefold());occupied.append(when)
            chosen.append({'contact_id':c['id'],'touch':n,'send_at':stamp(when),'status':'review','priority':round(priority,3)})
    chosen.sort(key=lambda x:x['send_at'])
    return {'date':day,'capacity':capacity,'sent':len(completed),'remaining_capacity':max(0,capacity-len(completed)-len(chosen)),'actions':chosen,'new':sum(x['touch']==1 for x in chosen),'followups':sum(x['touch']>1 for x in chosen),'held':held,'sending_enabled':False}


def review_action(db,action_id,status,expected_hash=None,now=None):
    now=instant(now or datetime.now(timezone.utc))
    if status not in {'approved','skipped','review','held'}: raise ValueError('Review cannot send')
    with db:
        row=db.execute('SELECT * FROM scheduled_sends WHERE id=?',(action_id,)).fetchone()
        if not row or row['status'] not in {'review','approved','held'}: raise ValueError('Only current review items can be reviewed')
        c=get(db,row['contact_id'])
        if c['status'] in TERMINAL|{'REPLIED'}: raise ValueError('Conversation changed; action canceled')
        if status=='approved':
            from readiness import blockers
            issues=blockers(json.loads(c['context']),row['subject'],row['body'],row['touch_number'])
            if c['engine']=='technical_contract' and row['touch_number']>1:
                from followup_lint import blockers as followup_blockers,day_for
                issues+=followup_blockers(db,c,row['body'] or '',day_for(dict(row)),row['id'])
            if issues: raise ValueError('; '.join(x['label'] for x in issues))
            ok,why=eligible(db,c,now)
            if not ok: raise ValueError(why)
        if status=='approved' and row['send_at'] and instant(row['send_at'])<now: raise ValueError('Recommendation has passed; rebuild the future queue')
        from execution import schema,approve
        schema(db)
        if status=='approved': approve(db,action_id,expected_hash,now)
        else: db.execute('DELETE FROM execution_approvals WHERE action_id=?',(action_id,))
        db.execute('UPDATE scheduled_sends SET status=?,reviewed_at=? WHERE id=?',(status,stamp(now) if status=='approved' else None,action_id))
        event(db,c['id'],'review',f'{status} · action {action_id}')
    return {'status':status,'send_authorized':False,'schedule_authorized':status=='approved'}


def orphaned_relationships(db):
    result=[]
    for row in db.execute("SELECT * FROM contacts WHERE status NOT IN ('RESEARCHED','BOUNCED','UNSUBSCRIBED','DECLINED','COMPLETE')"):
        c=dict(row)
        if not c['touch_number'] and c['rank']>1: continue
        if c['next_action_at']: continue
        if db.execute("SELECT 1 FROM scheduled_sends WHERE contact_id=? AND status IN ('review','approved','needs_draft','held','gmail_scheduled','cancel_required')",(c['id'],)).fetchone(): continue
        if db.execute('SELECT 1 FROM settings WHERE key=?',('company_pause:'+company_key(c),)).fetchone(): continue
        result.append({k:c[k] for k in ('id','campaign','account_id','person_id','engine','name','status')})
    return result


def revoke_invalid_approvals(db,now=None):
    """Keep persisted approval state consistent with current, content-bound gates."""
    from readiness import blockers
    from scheduling import validate_send_time
    from execution import schema,action_record,digest
    schema(db)
    for row in db.execute("SELECT * FROM scheduled_sends WHERE status IN ('approved','gmail_scheduled')").fetchall():
        c=get(db,row['contact_id']);ctx=json.loads(c['context'])
        problems=blockers(ctx,row['subject'],row['body'] or '',row['touch_number'])
        if c['engine']=='technical_contract' and row['touch_number']>1:
            from followup_lint import blockers as followup_blockers,day_for
            problems+=followup_blockers(db,c,row['body'] or '',day_for(dict(row)),row['id'])
        # An elapsed time on an already scheduled message requires Sent reconciliation,
        # not cancellation on that basis alone. Text/check changes still require cancellation.
        if row['status']=='approved': problems+=validate_send_time(ctx,row['send_at'],now)
        approval=db.execute('SELECT approval_hash FROM execution_approvals WHERE action_id=?',(row['id'],)).fetchone()
        if row['status']=='approved' and (not approval or approval['approval_hash']!=digest(action_record(db,row['id']))):
            problems.append({'code':'approval','label':'Approved record changed'})
        if not problems: continue
        reason='; '.join(p['label'] for p in problems)
        status='cancel_required' if row['status']=='gmail_scheduled' else 'held'
        db.execute('UPDATE scheduled_sends SET status=?,reviewed_at=NULL,decision=? WHERE id=?',(status,reason,row['id']))
        db.execute('DELETE FROM execution_approvals WHERE action_id=?',(row['id'],))
        db.execute("UPDATE gmail_executions SET state=? WHERE action_id=?",('cancel_required' if status=='cancel_required' else 'reconcile',row['id']))
        event(db,c['id'],'approval_revoked',f'Action {row["id"]}: '+reason,now)


def projection(db):
    revoke_invalid_approvals(db)
    contacts=[dict(r) for r in db.execute('SELECT id,campaign,account_id,person_id,engine,status,touch_number,first_sent_at,last_outbound_at,last_inbound_at,next_action_at,reply_type,snapshot_at FROM contacts')]
    sends=[dict(r) for r in db.execute('''SELECT s.*,c.name,c.email,c.campaign,c.account_id,c.person_id,c.engine,c.recipient_timezone FROM scheduled_sends s JOIN contacts c ON c.id=s.contact_id WHERE s.status IN ('review','approved','needs_draft','held','gmail_scheduled','cancel_required') ORDER BY send_at''')]
    from readiness import blockers
    from campaign_lint import check as check_batch
    batches={campaign:check_batch(db,campaign) for campaign in {s['campaign'] for s in sends}}
    for send in sends:
        c=get(db,send['contact_id']);ctx=json.loads(c['context']);send['blockers']=blockers(ctx,send['subject'],send['body'] or '',send['touch_number'])
        if c['engine']=='technical_contract' and send['touch_number']>1:
            from followup_lint import blockers as followup_blockers,day_for
            send['blockers']+=followup_blockers(db,c,send['body'] or '',day_for(send),send['id'])
        from scheduling import validate_send_time
        send['blockers']+=validate_send_time(ctx,send['send_at'])
        from readiness import check_states
        send['checks']=check_states(ctx,send['subject'],send['body'] or '')
        batch=batches[send['campaign']]
        if not batch['eligible_for_approval']:
            relevant=[x['label'] for x in batch['unresolved'] if send['id'] in x['action_ids']]
            send['blockers'].append({'code':'campaign_review','label':'; '.join(relevant) or 'Current batch needs its campaign-level review'})
        from execution import action_record,digest,mailbox_policy
        record=action_record(db,send['id']);send['approval_hash']=digest(record)
        send['sender_mailbox']=record['sender_mailbox'];send['labels']=record['labels']
        send['attachment_filenames']=[a['filename'] for a in record['attachments']]
        expected_sender=mailbox_policy(c['engine']).get('sender_mailbox')
        if not expected_sender or expected_sender!=c['sender_mailbox']:send['blockers'].append({'code':'sender','label':'Confirm the workspace sender mailbox'})
        if send['status']=='cancel_required':send['blockers'].insert(0,{'code':'cancel_required','label':'Cancel this scheduled email in Gmail; a reply or stop condition invalidated it'})
    timeline=[dict(r) for r in db.execute('SELECT * FROM activities ORDER BY at DESC LIMIT 500')]
    metrics=[dict(r) for r in db.execute('''SELECT c.engine,json_extract(c.context,'$.role') role,json_extract(c.context,'$.company_type') company_type,m.touch_number,
       COUNT(DISTINCT CASE WHEN m.kind IN ('sent','sent_reported') THEN c.id||'/'||m.touch_number END) sent,
       COUNT(DISTINCT CASE WHEN m.kind='sent' THEN c.id||'/'||m.touch_number END) verified_sent,
       COUNT(DISTINCT CASE WHEN m.kind='sent_reported' THEN c.id||'/'||m.touch_number END) reported_sent,
       COUNT(DISTINCT CASE WHEN m.outcome IN ('positive','routing','technical_answer','meeting_proposed','meeting_confirmed','next_step') THEN c.sender_mailbox||'/'||c.thread_id END) useful_replies,
       COUNT(DISTINCT CASE WHEN m.outcome IN ('meeting_proposed','meeting_confirmed') THEN c.sender_mailbox||'/'||c.thread_id END) meetings
       FROM messages m JOIN contacts c ON c.id=m.contact_id GROUP BY c.engine,role,company_type,m.touch_number''')]
    runs=[dict(r) for r in db.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 5')]
    return {'contacts':contacts,'queue':sends,'timeline':timeline,'metrics':metrics,'runs':runs,'orphaned_relationships':orphaned_relationships(db),'sending_enabled':False}
