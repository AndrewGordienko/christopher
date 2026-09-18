import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mission import merge_queue_view


class LocalRevisionTests(unittest.TestCase):
    def setUp(self):
        self.person = {'subject': 'A project', 'body': 'Restored thought',
                       'blockers': [{'code': 'external_critic', 'label': 'External critic stale after edit'}], 'schedule': {}}
        self.queue = {'id': 7, 'touch_number': 1, 'subject': 'A project',
                      'body': 'Earlier wording', 'approval_hash': 'approved-old-copy',
                      'status': 'gmail_scheduled', 'send_at': '2026-09-16T09:17:00Z',
                      'sender_mailbox': 'sender@example.com', 'labels': ['Scheduled'],
                      'attachment_filenames': ['resume.pdf'], 'blockers': []}

    def test_local_revision_cannot_inherit_old_approval(self):
        untouched = copy.deepcopy(self.queue)
        merge_queue_view(self.person, self.queue)
        self.assertEqual(self.queue, untouched)
        self.assertEqual(self.person['body'], 'Restored thought')
        self.assertEqual(self.person['draft_status'], 'local_revision')
        self.assertIsNone(self.person['approval_hash'])
        self.assertEqual(self.person['scheduled_version']['body'], 'Earlier wording')
        self.assertIn('External critic stale after edit', [b['label'] for b in self.person['blockers']])

    def test_unchanged_copy_keeps_actual_schedule(self):
        self.person['body'] = self.queue['body']
        merge_queue_view(self.person, self.queue)
        self.assertEqual(self.person['draft_status'], 'gmail_scheduled')
        self.assertEqual(self.person['approval_hash'], 'approved-old-copy')
        self.assertNotIn('has_local_revision', self.person)

    def test_subject_change_also_invalidates_local_approval(self):
        self.person.update(body=self.queue['body'], subject='Another thought')
        merge_queue_view(self.person, self.queue)
        self.assertIsNone(self.person['approval_hash'])
        self.assertTrue(self.person['has_local_revision'])

    def test_followup_does_not_compare_against_initial_copy(self):
        self.queue['touch_number'] = 2
        self.person['draft_status'] = 'sent'
        merge_queue_view(self.person, self.queue)
        self.assertEqual(self.person['draft_status'], 'sent')
        self.assertNotIn('has_local_revision', self.person)

    def test_held_queue_remains_visibly_held_with_archived_local_copy(self):
        self.queue.update(status='held',body=None,approval_hash=None)
        merge_queue_view(self.person,self.queue)
        self.assertEqual(self.person['draft_status'],'held')
        self.assertEqual(self.person['schedule']['status'],'held')
        self.assertTrue(self.person['has_local_revision'])
        self.assertIsNone(self.person['approval_hash'])
        self.assertEqual(self.person['body'],'Restored thought')
