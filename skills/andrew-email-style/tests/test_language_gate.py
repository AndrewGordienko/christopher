import json,sys,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from readiness import blockers,fingerprint,check_states,language_findings
from scheduling import validate_send_time
from state import get,revoke_invalid_approvals,review_action
from execution import approved_record,claim
import test_execution as execution_tests
NOW=execution_tests.NOW

class LanguageGateTests(unittest.TestCase):
 def context(self,body='An ordinary email.'):
  fp=fingerprint('Subject',body)
  return {'email':'person@example.test','email_status':'verified','timezone':'Europe/London',
   'timezone_source':'person_location','timezone_source_id':'source-1','facts_supported':True,
   'factual_review_hash':fp,'final_checks':{'draft_hash':fp,'reviewed_at':NOW.isoformat(),'reviewer':'fixture',
   'grammar':{'passed':True},'voice':{'passed':True},'facts':{'passed':True}}}
 def test_missing_review_is_not_inferred_from_empty_lint(self):
  ctx=self.context();ctx.pop('final_checks')
  self.assertEqual(language_findings('An ordinary email.'),[])
  self.assertIn('grammar',{x['code'] for x in blockers(ctx,'Subject','An ordinary email.')})
 def test_every_text_change_invalidates_all_final_checks(self):
  ctx=self.context()
  self.assertEqual(blockers(ctx,'Subject','An ordinary email.'),[])
  for sub,body in [('Other','An ordinary email.'),('Subject','An ordinary email!')]:
   self.assertEqual(check_states(ctx,sub,body)['grammar'],'stale after edit')
   self.assertTrue({'facts','grammar','voice'}<={x['code'] for x in blockers(ctx,sub,body)})
 def test_external_review_cannot_pass_with_an_old_hash_or_no_receipt(self):
  ctx=self.context();ctx.update(external_critic_required=True,external_critic_review={
   'status':'reviewed','after_hash':'old','observed_at':NOW.isoformat(),'feedback':'Actual fixture feedback','chat_url':'https://chatgpt.com/c/fixture'})
  self.assertIn('external_critic',{x['code'] for x in blockers(ctx,'Subject','An ordinary email.')})
  ctx['external_critic_review']['after_hash']=fingerprint('Subject','An ordinary email.')
  self.assertEqual(blockers(ctx,'Subject','An ordinary email.'),[])
  del ctx['external_critic_review']['chat_url']
  self.assertIn('external_critic',{x['code'] for x in blockers(ctx,'Subject','An ordinary email.')})
 def test_known_broken_coordination_and_comma_cannot_pass(self):
  for body in ['I’m in London, UK working on simulation.','I’d be doing this alongside my current work and attached my resume.','Enthought interested me as somewhere I could work.']:
   self.assertTrue(language_findings(body))
 def test_project_critic_receipt_requires_real_chat_url_and_current_text(self):
  ctx=self.context();ctx['external_critic_review']={'status':'reviewed','after_hash':fingerprint('Subject','An ordinary email.'),'observed_at':NOW.isoformat(),'feedback':['PASS'],'chat_url':'https://chatgpt.com/g/g-p-morrow/c/review-id'}
  self.assertEqual(check_states(ctx,'Subject','An ordinary email.')['external'],'passed')
  self.assertEqual(check_states(ctx,'Subject','Changed email.')['external'],'stale after edit')
  for url in ['https://chatgpt.com/g/g-p-morrow','https://chatgpt.com.evil.test/g/g-p-morrow/c/review-id']:
   ctx['external_critic_review']['chat_url']=url
   self.assertEqual(check_states(ctx,'Subject','An ordinary email.')['external'],'pending')
 def test_actual_recipient_time_rejects_overnight_and_missing_provenance(self):
  ctx=self.context();ctx['timezone']='Asia/Kolkata'
  self.assertTrue(validate_send_time(ctx,'2026-09-14T22:00:00Z',NOW)) # 03:30 next day
  self.assertFalse(validate_send_time(ctx,'2026-09-15T04:00:00Z',NOW)) # 09:30
  ctx.pop('timezone_source_id')
  self.assertTrue(validate_send_time(ctx,'2026-09-15T04:00:00Z',NOW))

class ApprovalRevocationTests(unittest.TestCase):
 setUp=execution_tests.ExecutionTests.setUp
 tearDown=execution_tests.ExecutionTests.tearDown
 approve=execution_tests.ExecutionTests.approve
 def test_stale_external_check_revokes_persisted_approval(self):
  self.approve();ctx=json.loads(get(self.db,self.cid)['context'])
  ctx.update(external_critic_required=True,external_critic_review={'status':'reviewed','after_hash':'old'})
  self.db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(ctx),self.cid))
  revoke_invalid_approvals(self.db,NOW);self.db.commit()
  self.assertEqual(self.db.execute('SELECT status FROM scheduled_sends WHERE id=?',(self.q['id'],)).fetchone()[0],'held')
  self.assertIsNone(self.db.execute('SELECT 1 FROM execution_approvals WHERE action_id=?',(self.q['id'],)).fetchone())
  with self.assertRaises(ValueError):claim(self.db,self.q['id'],self.q['approval_hash'],NOW)
 def test_changed_copy_after_scheduling_requires_cancellation(self):
  self.approve();self.db.execute("UPDATE scheduled_sends SET status='gmail_scheduled',body=body||' Edit' WHERE id=?",(self.q['id'],))
  revoke_invalid_approvals(self.db,NOW)
  self.assertEqual(self.db.execute('SELECT status FROM scheduled_sends WHERE id=?',(self.q['id'],)).fetchone()[0],'cancel_required')

if __name__=='__main__':unittest.main()
