import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from external_critic import summary,fingerprint

class ExternalCriticTests(unittest.TestCase):
    def test_review_belongs_to_exact_current_subject_and_body(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            self.assertEqual(summary(p,'Subject','Body'),'not run')
            r={'status':'reviewed','chat_url':'https://chatgpt.com/c/example','observed_at':'2026-09-14T18:00:00Z','feedback':'No change.','after_hash':fingerprint('Subject','Body'),'accepted_fixes':[]}
            (p/'external-critic.json').write_text(json.dumps(r))
            self.assertEqual(summary(p,'Subject','Body'),'reviewed · retained')
            self.assertEqual(summary(p,'New subject','Body'),'stale after edit')
            self.assertEqual(summary(p,'Subject','New body'),'stale after edit')

    def test_missing_receipt_does_not_claim_review(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'external-critic.json').write_text(json.dumps({'status':'reviewed','after_hash':fingerprint('S','B')}))
            self.assertEqual(summary(p,'S','B'),'receipt incomplete')
