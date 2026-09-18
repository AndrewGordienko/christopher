import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manual_sent import record, receipts
from state import connect, register, get, projection
from mission import mark_sent, review_catalog

NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


class ManualSentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / '.runtime/outbound.sqlite3'
        self.db = connect(self.path)
        self.cid = register(self.db, 'test', 'company', 'person', 'technical_contract', 'company',
                            {'name': 'Test Person', 'email': 'person@example.test',
                             'sender_mailbox': 'me@example.test', 'subject': 'Test project',
                             'body': 'The displayed draft.', 'timezone': 'Europe/London'}, NOW)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def report(self, **changes):
        values = dict(subject='Test project', body='The displayed draft.', sender='me@example.test',
                      recipient='person@example.test', sent_at=NOW.isoformat(), request_id='test-request', now=NOW)
        values.update(changes)
        return record(self.db, self.cid, **values)

    def test_persists_user_evidence_and_contacted_company(self):
        result = self.report()
        self.assertTrue(result['company_contacted'])
        c = get(self.db, self.cid)
        self.assertEqual((c['status'], c['touch_number']), ('AWAITING_REPLY', 1))
        self.assertEqual(c['first_sent_at'], NOW.isoformat())
        self.assertEqual(c['next_action_at'], (NOW + timedelta(days=3)).isoformat())
        receipt = receipts(self.db)[0]
        self.assertEqual(receipt['source'], 'user_action:a.outbound.mark_as_sent')
        self.assertEqual(receipt['body'], 'The displayed draft.')
        self.assertIsNone(c['thread_id'])
        # The company projection must use persisted contact state, including after reload.
        folder = self.root / 'campaigns/test'
        folder.mkdir(parents=True)
        (folder / 'campaign.json').write_text('{}')
        (folder / 'mission.json').write_text('{}')
        person = {'id': 'person', 'subject': receipt['subject'], 'body': receipt['body'], 'readiness_context': {}}
        data = {'id': 'test', 'engine': 'technical_contract', 'counts': {},
                'accounts': [{'id': 'company', 'contacts': [person]}]}
        with patch('mission.review_campaign', return_value=data):
            view = review_catalog(self.root)
        account = view['campaigns'][0]['accounts'][0]
        self.assertTrue(account['contacted'])
        self.assertEqual(account['first_contacted_at'], NOW.isoformat())
        self.assertEqual(account['contacts'][0]['draft_status'], 'sent')

    def test_retry_and_later_gmail_verification_do_not_double_count(self):
        self.report()
        self.assertEqual(self.report(request_id='retry')['status'], 'already_recorded')
        self.assertEqual(len(receipts(self.db)), 1)
        self.db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',
                        (self.cid, 'observed-gmail-message', 'sent', NOW.isoformat(), 1, None))
        self.db.commit()
        metrics = projection(self.db)['metrics']
        self.assertEqual(sum(m['sent'] for m in metrics), 1)
        self.assertEqual(sum(m['verified_sent'] for m in metrics), 1)
        self.assertEqual(sum(m['reported_sent'] for m in metrics), 1)
        with self.assertRaisesRegex(ValueError, 'different email'):
            self.report(body='Different copy', request_id='another')

    def test_invalid_future_or_recipient_changes_cannot_record_send(self):
        for changes in ({'sent_at': (NOW + timedelta(minutes=1)).isoformat()},
                        {'recipient': 'wrong@example.test'}, {'touch': 2}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.report(**changes)
        self.assertEqual(get(self.db, self.cid)['touch_number'], 0)
        self.assertEqual(receipts(self.db), [])

    def test_pending_gmail_schedule_requires_reconciliation(self):
        self.db.execute('INSERT INTO scheduled_sends(contact_id,touch_number,status,subject,body) VALUES(?,?,?,?,?)',
                        (self.cid, 1, 'gmail_scheduled', 'Earlier subject', 'Earlier body'))
        self.db.commit()
        result = self.report()
        self.assertTrue(result['gmail_reconciliation_required'])
        row = self.db.execute('SELECT * FROM scheduled_sends').fetchone()
        self.assertEqual(row['status'], 'cancel_required')
        self.assertEqual(row['body'], 'Earlier body')
        self.assertEqual(get(self.db, self.cid)['touch_number'], 1)

    def test_recording_past_send_does_not_reopen_reply_or_terminal_state(self):
        self.db.execute("UPDATE contacts SET status='REPLIED',recommended_action='REVIEW_REPLY',next_action_at=? WHERE id=?",
                        (NOW.isoformat(), self.cid))
        self.db.commit()
        self.report(sent_at=(NOW - timedelta(days=2)).isoformat())
        c = get(self.db, self.cid)
        self.assertEqual(c['status'], 'REPLIED')
        self.assertEqual(c['recommended_action'], 'REVIEW_REPLY')
        self.assertEqual(c['next_action_at'], NOW.isoformat())

    def test_api_rejects_stale_displayed_copy(self):
        data = {'accounts': [{'id': 'company', 'contacts': [{'id': 'person', 'subject': 'Test project',
                  'body': 'Current draft.', 'email': 'person@example.test'}]}]}
        stale_hash = hashlib.sha256(b'Test project\n\nThe displayed draft.').hexdigest()
        with patch('mission.review_campaign', return_value=data), patch('state.connect', return_value=self.db):
            with self.assertRaisesRegex(ValueError, 'displayed email changed'):
                mark_sent(Path('test'), 'company', 'person', {'draft_hash': stale_hash})
        self.assertEqual(get(self.db, self.cid)['touch_number'], 0)
