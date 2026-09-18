import sys
import json
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from followup_lint import text_findings, shared_runs, blockers, current_reference
from test_followup_drafts import FollowupDraftTests, NOW
from state import get


class FollowupTextTests(unittest.TestCase):
    def codes(self,text,**kwargs):return {i['code'] for i in text_findings(text,**kwargs)}

    def test_still_rejects_reintroduction_and_compound_questions(self):
        text="Hi A,\n\nI'm a UofT student on co-op in London.\n\nCould we do a project? Can we have a call?"
        codes=self.codes(text,original="I'm a UofT student on co-op in London.")
        self.assertTrue({'followup_biography','followup_questions'}<=codes)

    def test_proposed_window_does_not_require_a_recipient_scoped_project(self):
        for scope in ['4–6 weeks','4-6 weeks','4 to 6 weeks','four to six weeks']:
            self.assertEqual(text_findings('If a useful task fits into '+scope+', I could take ownership of it.'),[])

    def test_chosen_examples_fit_ceiling_and_longer_copy_is_flagged(self):
        ref=current_reference()
        self.assertEqual(text_findings(ref['body']),[])
        examples=Path(__file__).resolve().parents[2]/'paid-contract-followup-editor/references/chosen-scheduled-examples.json'
        for example in json.loads(examples.read_text())['examples']:
            self.assertEqual(text_findings(example['body']),[],example['recipient'])
        extra=ref['max_words']-len(ref['body'].split())+1
        self.assertIn('followup_length',self.codes(ref['body']+' context'*extra))

    def test_approved_context_may_repeat_but_company_copy_is_checked(self):
        shared='\n\n'.join(current_reference()['approved_shared_spans'][:2])
        rows=[{'id':'a','company_key':'one','body':shared+'\n\nAir quality matters to me.'},
              {'id':'b','company_key':'two','body':shared+'\n\nGrid reliability is why I wrote.'}]
        self.assertEqual(shared_runs(rows),{})
        run='These are fifteen ordinary words which should never appear together in two different company drafts'
        for row in rows:row['body']+='\n\n'+run
        self.assertEqual(set(shared_runs(rows)),{'a','b'})

    def test_guarantees_fail_but_ownership_and_pace_pass(self):
        self.assertIn('followup_guarantee',self.codes('I guarantee positive results quickly.'))
        self.assertIn('followup_guarantee',self.codes('Guaranteed results in four weeks.'))
        self.assertEqual(text_findings('I work pretty intensely and am used to getting to something concrete quickly.'),[])

    def test_short_relevant_proof_and_one_question_pass(self):
        text="Hi Kevin,\n\nI've been building recovery search for robotic workflows, starting from the state the machine has reached.\n\nDoes keeping the remaining delivery route intact make replanning much harder?\n\nBest,\nAndrew"
        self.assertEqual(text_findings(text),[])

    def test_repetition_uses_exact_word_runs_across_companies(self):
        run='These are fifteen ordinary words which should never appear together in two different company drafts'
        a={'id':'a','company_key':'one','body':'Hi Alice, '+run}
        b={'id':'b','company_key':'two','body':'Hi Bob, '+run.upper().replace(' ', '\n')}
        self.assertEqual(set(shared_runs([a,b])),{'a','b'})
        self.assertEqual(shared_runs([a,{**b,'company_key':'one'}]),{})
        self.assertEqual(shared_runs([a,{**b,'body':' '.join(run.split()[:14])}]),{})


class FollowupBoundaryTests(FollowupDraftTests):
    def test_coworker_scheduled_same_london_day_is_blocked_across_campaigns(self):
        other=self.contact('two')
        self.db.execute("UPDATE contacts SET campaign='another-campaign' WHERE id=?",(other,))
        self.db.execute("UPDATE scheduled_sends SET status='gmail_scheduled',send_at='2026-09-16T23:30:00+00:00',queue_date='2026-09-16',body='Could you clarify the sensor case?' WHERE contact_id=? AND touch_number=2",(other,));self.db.commit()
        codes={i['code'] for i in blockers(self.db,get(self.db,self.cid),'Is that the relevant recovery case?',day='2026-09-17')}
        self.assertIn('followup_company_day',codes)
        self.assertNotIn('followup_company_day',{i['code'] for i in blockers(self.db,get(self.db,self.cid),'Is that the relevant recovery case?',day='2026-09-18')})

    def test_execution_boundary_runs_followup_lint(self):
        from unittest.mock import patch
        from execution import validate_record
        self.db.execute("UPDATE scheduled_sends SET status='review',send_at='2026-09-17T10:00:00+00:00',body=? WHERE contact_id=? AND touch_number=2",('I guarantee positive results quickly.',self.cid));self.db.commit()
        aid=self.db.execute('SELECT id FROM scheduled_sends WHERE contact_id=? AND touch_number=2',(self.cid,)).fetchone()[0]
        with patch('campaign_lint.require_ready'),patch('execution.mailbox_policy',return_value={'sender_mailbox':'me@example.test'}),patch('execution.blockers',return_value=[]),patch('scheduling.validate_send_time',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Do not guarantee'):validate_record(self.db,aid,NOW)

if __name__=='__main__':unittest.main()
