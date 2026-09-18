"""Record a user's report of sending. Never send mail or invent Gmail evidence."""
from datetime import datetime, timedelta, timezone
import hashlib
from state import get, instant, stamp, event, TERMINAL, CADENCE


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS manual_send_receipts(
        id TEXT PRIMARY KEY, contact_id TEXT NOT NULL REFERENCES contacts(id),
        touch_number INTEGER NOT NULL, draft_hash TEXT NOT NULL,
        subject TEXT NOT NULL, body TEXT NOT NULL, sender TEXT NOT NULL,
        recipient TEXT NOT NULL, sent_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
        source TEXT NOT NULL, UNIQUE(contact_id,touch_number))''')


def record(db, cid, subject, body, sender, recipient, sent_at, request_id, touch=1, now=None):
    now = instant(now or datetime.now(timezone.utc))
    sent = instant(sent_at)
    if sent > now + timedelta(seconds=5):
        raise ValueError('Mark as sent records a past send, not a future schedule')
    if not subject.strip() or not body.strip() or not request_id or len(request_id) > 100:
        raise ValueError('A sent record needs the exact email and a request ID')
    if type(touch) is not int or touch < 1:
        raise ValueError('Invalid touch number')
    digest = hashlib.sha256((subject+'\n\n'+body).encode()).hexdigest()
    schema(db)
    with db:
        if not db.in_transaction:
            db.execute('BEGIN IMMEDIATE')
        c = get(db, cid)
        if sender != c['sender_mailbox'] or recipient != c['email']:
            raise ValueError('Sender or recipient changed; refresh the email')
        prior = db.execute('SELECT * FROM manual_send_receipts WHERE id=? OR (contact_id=? AND touch_number=?)',
                           (request_id, cid, touch)).fetchone()
        if prior:
            if prior['contact_id'] != cid or prior['touch_number'] != touch or prior['draft_hash'] != digest:
                raise ValueError('A different email is already recorded for this touch')
            return {'status': 'already_recorded', 'receipt': dict(prior), 'company_contacted': True}
        if c['touch_number'] >= touch:
            return {'status': 'already_recorded', 'source': 'existing_mail_record', 'company_contacted': True}
        if touch != c['touch_number'] + 1:
            raise ValueError('Cannot skip an unrecorded touch')
        if c['last_outbound_at'] and sent < instant(c['last_outbound_at']):
            raise ValueError('The send time precedes the previous touch')
        db.execute('INSERT INTO manual_send_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (request_id, cid, touch, digest, subject, body, sender, recipient,
                    stamp(sent), stamp(now), 'user_action:a.outbound.mark_as_sent'))
        db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',
                   (cid, 'user-reported:'+request_id, 'sent_reported', stamp(sent), touch, None))
        # User testimony is evidence of sending, but never proof a remote Gmail schedule was cancelled.
        queued = db.execute('SELECT * FROM scheduled_sends WHERE contact_id=? AND touch_number=?', (cid, touch)).fetchone()
        reconcile = bool(queued and queued['status'] in {'gmail_scheduled', 'cancel_required'})
        if queued:
            db.execute('UPDATE scheduled_sends SET status=?,decision=?,reviewed_at=NULL WHERE id=?',
                       ('cancel_required' if reconcile else 'sent_reported',
                        'User reported a send. Verify the Gmail schedule is no longer pending.' if reconcile else
                        'Sent reported by the user; not Gmail-verified.', queued['id']))
        first = c['first_sent_at'] or stamp(sent)
        due = stamp(max(instant(first)+timedelta(days=CADENCE[touch+1]), now)) if touch < 4 else None
        preserve = c['status'] in TERMINAL | {'REPLIED', 'OUT_OF_OFFICE'}
        db.execute('''UPDATE contacts SET touch_number=?,first_sent_at=?,last_outbound_at=?,
                      original_subject=COALESCE(original_subject,?),status=?,next_action_at=?,
                      recommended_action=?,updated_at=? WHERE id=?''',
                   (touch, first, stamp(sent), subject, c['status'] if preserve else 'AWAITING_REPLY',
                    c['next_action_at'] if preserve else due,
                    c['recommended_action'] if preserve else 'SYNC_MAILBOX', stamp(now), cid))
        event(db, cid, 'sent_reported', 'User marked touch '+str(touch)+' sent · '+request_id, sent)
        event(db, cid, 'company_contacted', 'Contacted via '+(c['name'] or recipient)+' · user report '+request_id, sent)
        if reconcile:
            event(db, cid, 'gmail_reconciliation_needed', 'Verify the earlier Gmail schedule after manual send · '+request_id, now)
    return {'status': 'sent_reported', 'company_contacted': True,
            'gmail_reconciliation_required': reconcile, 'sent_at': stamp(sent)}


def receipts(db):
    schema(db)
    return [dict(r) for r in db.execute('SELECT * FROM manual_send_receipts ORDER BY recorded_at DESC')]
