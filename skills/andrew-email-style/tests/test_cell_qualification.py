import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from cell_qualification import CRITERIA, SKEPTIC_ANSWERS, context, validate, qualification_blockers, review_blockers
from readiness import fingerprint, blockers
from research import writer_packet
from state import connect, register, sync_thread, build_queue
from test_workflow import brief

NOW = datetime(2026, 9, 15, 9, tzinfo=timezone.utc)


def qualified_context(facility='site', subject='Robot recovery', body='Synthetic test email', person='kim'):
    # Synthetic conversation evidence, not a real facility or prospect.
    fact = {'id':'observed-cell', 'entity_id':facility,
            'text':'Synthetic operator interview: Cell A is operating; twice per shift Kim resets a sequence timeout. State and actions are logged; recovery delays sorting.',
            'evidence':[{'source_id':'synthetic-interview', 'quote':'Synthetic operator interview'}]}
    record = {'schema_version':1, 'status':'QUALIFIED', 'qualification_score':7, 'facility_id':facility,
              'cell':{'id':facility+'-a', 'name':'Cell A', 'equipment':'Test sorting robot', 'task':'Sort containers'},
              'criteria':{k:{'status':'CONFIRMED', 'statement':'Synthetic sourced finding for '+k,
                             'basis':['observed-cell']} for k in CRITERIA},
              'reason':'Synthetic qualified recovery case', 'reviewer':'test fixture', 'reviewed_at':NOW.isoformat(),
              'physical_only':False, 'requires_safety_bypass':False, 'next_action':'Synthetic observation scope'}
    record['criteria']['technical_owner']['person_id'] = person
    ctx = context({'facility':{'id':facility}, 'facts':[fact], 'cell_qualification':record})
    review = {'passed':True, 'reviewer':'test fixture', 'reviewed_at':NOW.isoformat(), 'reason':'Synthetic separate review'}
    ctx['outbound_reviews'] = {'draft_hash':fingerprint(subject, body), 'qualification_hash':ctx['cell_qualification_hash'],
                              'thought_continuity':dict(review), 'cold_email_skeptic':dict(review, answers={k:'Synthetic supported explanation' for k in SKEPTIC_ANSWERS})}
    return ctx


class CellQualificationTests(unittest.TestCase):
    def test_complete_evidence_passes_and_score_cannot_replace_missing_evidence(self):
        ctx=qualified_context(); self.assertEqual(qualification_blockers(ctx), [])
        q=ctx['cell_qualification']; q['criteria']['software_recovery'].update(status='UNKNOWN', basis=[])
        self.assertTrue(qualification_blockers(ctx))
        q['qualification_score']=6
        with self.assertRaisesRegex(ValueError, 'all seven'):
            validate(q, ctx['cell_qualification_facts'], 'site')

    def test_likely_requires_evidence_and_reasoned_inference(self):
        ctx=qualified_context();q=ctx['cell_qualification'];q['criteria']['operating']['status']='LIKELY'
        with self.assertRaisesRegex(ValueError, 'inference'):validate(q,ctx['cell_qualification_facts'],'site')
        q['criteria']['operating']['inference']='Synthetic current operating evidence supports continuity.'
        validate(q,ctx['cell_qualification_facts'],'site')
        q['criteria']['operating']['basis']=[]
        with self.assertRaisesRegex(ValueError, 'evidence'):validate(q,ctx['cell_qualification_facts'],'site')

    def test_parent_automation_or_different_facility_cannot_qualify_cell(self):
        ctx=qualified_context();ctx['cell_qualification_facts']['observed-cell']['entity_id']='parent-company'
        with self.assertRaisesRegex(ValueError, 'facility/cell'):
            validate(ctx['cell_qualification'],ctx['cell_qualification_facts'],'site')

    def test_physical_only_and_safety_bypass_cases_are_held(self):
        for key in ('physical_only','requires_safety_bypass'):
            ctx=qualified_context();q=ctx['cell_qualification'];q[key]=True
            with self.assertRaisesRegex(ValueError, 'must be HOLD'):validate(q,ctx['cell_qualification_facts'],'site')
            q['status']='HOLD';validate(q,ctx['cell_qualification_facts'],'site')
            self.assertTrue(qualification_blockers(ctx))

    def test_evidence_change_invalidates_qualification(self):
        ctx=qualified_context();ctx['cell_qualification_facts']['observed-cell']['text']='Changed observation'
        self.assertIn('changed',qualification_blockers(ctx)[0]['label'])

    def test_text_or_qualification_change_invalidates_separate_reviews(self):
        ctx=qualified_context();d=fingerprint('Robot recovery','Synthetic test email')
        self.assertEqual(review_blockers(ctx,d),[])
        self.assertEqual(len(review_blockers(ctx,fingerprint('Different subject','Synthetic test email'))),2)
        ctx['cell_qualification_hash']='new-evidence'
        self.assertEqual(len(review_blockers(ctx,d)),2)

    def test_skeptic_requires_all_six_answers(self):
        ctx=qualified_context();del ctx['outbound_reviews']['cold_email_skeptic']['answers']['routing_reply']
        self.assertEqual(review_blockers(ctx,fingerprint('Robot recovery','Synthetic test email'))[0]['code'],'cold_email_skeptic')

    def test_legacy_automation_yes_cannot_invoke_writer(self):
        b=brief();b.update(engine='wapahki_facility',facility={'id':'test-co','name':'Test site','location':'Test location',
                        'subvertical':'material_recovery','fact_ids':['f1'],'automation':[{'fact_ids':['f1']}]})
        sources={'s1':{'text':'Test Company has a sorting robot. Kim manages automation.'}}
        with self.assertRaisesRegex(ValueError,'Cell qualification'):writer_packet(b,sources,'kim')

    def test_queue_rejects_missing_qualification_even_with_verified_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=connect(Path(tmp)/'state.sqlite3')
            ctx={'name':'Kim','email':'kim@example.test','sender_mailbox':'me@example.test','timezone':'America/Toronto',
                 'qualified':True,'email_status':'verified','subject':'Robot recovery','body':'Synthetic test email','rank':1}
            cid=register(db,'synthetic','site','kim','wapahki_facility','site',ctx,NOW)
            sync_thread(db,cid,{'account':'me@example.test','id':None,'complete':True,'source':'https://mail.google.com/test',
                               'tool_ref':'synthetic test','observed_at':NOW.isoformat(),'messages':[]})
            self.assertEqual(build_queue(db,'2026-09-16',30,NOW)['actions'],[])
            ctx.update(qualified_context());register(db,'synthetic','site','kim','wapahki_facility','site',ctx,NOW)
            self.assertEqual(len(build_queue(db,'2026-09-16',30,NOW)['actions']),1)
            db.close()

    def test_contract_work_does_not_inherit_robot_gate(self):
        ctx={'engine':'technical_contract'}
        self.assertNotIn('cell_qualification',{x['code'] for x in blockers(ctx,'Work','Hello')})

    def test_followup_cannot_reuse_first_touch_critic_for_different_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=connect(Path(tmp)/'state.sqlite3')
            ctx={'name':'Kim','email':'kim@example.test','sender_mailbox':'me@example.test','timezone':'America/Toronto',
                 'qualified':True,'email_status':'verified','subject':'Robot recovery','body':'Synthetic test email','rank':1,
                 **qualified_context()}
            cid=register(db,'synthetic','site','kim','wapahki_facility','site',ctx,NOW)
            decision={'action':'SEND','snapshot_at':NOW.isoformat(),'research_version':None,
                      'decided_at':NOW.isoformat(),'body':'A different synthetic follow-up'}
            with db:
                db.execute("UPDATE contacts SET touch_number=1,next_action_at=?,snapshot_at=?,decision=? WHERE id=?",
                           (NOW.isoformat(),NOW.isoformat(),json.dumps(decision),cid))
            result=build_queue(db,'2026-09-16',30,NOW)
            self.assertEqual(result['actions'],[])
            self.assertTrue(any('review pending or stale' in x['reason'] for x in result['held']))
            ctx['outbound_reviews']['draft_hash']=fingerprint('Robot recovery',decision['body'])
            with db:
                db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(ctx),cid))
            refreshed=build_queue(db,'2026-09-16',30,NOW)
            self.assertEqual(len(refreshed['actions']),1)
            self.assertEqual(refreshed['actions'][0]['touch'],2)
            db.close()


if __name__=='__main__':unittest.main()
