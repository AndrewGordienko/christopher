from datetime import datetime,timezone,timedelta
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from campaign_lint import lint,batch_fingerprint,SEMANTIC_CHECKS,save_review,check
from scheduling import recommend_send,resolve_timezone
from readiness import blockers,fingerprint


class CampaignTests(unittest.TestCase):
 def rows(self):
  return [dict(id=i,contact_id=str(i),recipient=f'{i}@example.test',company_key=str(i),status='review',sender_mailbox='andrew@example.test',recipient_timezone='Europe/London',subject=f'Technical topic {i}',body=f"Hi Person,\n\nI'm a UofT student on co-op in London, UK.\n\nDistinct question {i}.\n\nBest,\nAndrew",send_at=None) for i in range(6)]
 def test_biography_is_not_a_repetition_failure(self):
  self.assertEqual(lint(self.rows())['issues'],[])
 def test_same_scaffold_and_regular_batch_are_detected(self):
  rows=self.rows()
  for i,r in enumerate(rows):
   r['body']+="\n\nOne thought was an evaluation harness. I was wondering if there might be a project."
   r['send_at']=f'2026-09-15T08:{i*10:02d}:00+00:00'
  codes={x['code'] for x in lint(rows)['issues']}
  self.assertTrue({'one_thought','wondering_ask','harness','regular_spacing','round_batch'}<=codes)
 def test_account_collision_cannot_be_waived_as_style(self):
  rows=self.rows();rows[0]['company_key']=rows[1]['company_key'];rows[0]['send_at']='2026-09-15T08:31:00Z';rows[1]['send_at']='2026-09-15T09:07:00Z'
  issue=next(x for x in lint(rows)['issues'] if x['code']=='account_collision')
  self.assertEqual(issue['severity'],'error')
 def test_review_fingerprint_changes_for_actual_record_changes_only(self):
  rows=self.rows();before=batch_fingerprint(rows)
  rows[0]['status']='approved';self.assertEqual(before,batch_fingerprint(rows))
  rows[0]['body']+=' Changed';self.assertNotEqual(before,batch_fingerprint(rows))
 def test_semantic_review_is_required_and_stale_after_copy_change(self):
  rows=self.rows();db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
  with patch('campaign_lint.rows_for',return_value=rows):
   self.assertFalse(check(db,'wave')['eligible_for_approval'])
   review={'fingerprint':batch_fingerprint(rows),'reason':'Compared the actual technical questions','semantic_checks':dict.fromkeys(SEMANTIC_CHECKS,True),'resolutions':{}}
   self.assertTrue(save_review(db,'wave',review)['eligible_for_approval'])
   rows[0]['subject']='Changed subject'
   self.assertFalse(check(db,'wave')['eligible_for_approval'])
   with self.assertRaises(ValueError):save_review(db,'wave',review)
  db.close()
 def test_timezone_fallback_and_unknown_source(self):
  places=[{'source':'apollo_timezone','source_id':'a','timezone':'America/New_York'},{'source':'relevant_facility','source_id':'b','timezone':'Europe/Berlin'}]
  self.assertEqual(resolve_timezone(places)['timezone'],'Europe/Berlin')
  self.assertIsNone(resolve_timezone([{'source':'sender_location','source_id':'a','timezone':'Europe/London'}])['timezone'])
 def test_morning_window_dst_spacing_and_capacity(self):
  now=datetime(2026,10,30,22,tzinfo=timezone.utc);occupied=[]
  for i in range(12):
   r=recommend_send({'timezone':'America/New_York'},str(i),now,occupied=occupied)
   local=datetime.fromisoformat(r['recommended_send_local']);utc=datetime.fromisoformat(r['recommended_send_utc'].replace('Z','+00:00'))
   self.assertLess(local.weekday(),5);self.assertTrue(510<=local.hour*60+local.minute<=690)
   self.assertEqual(local.utcoffset(),timedelta(hours=-5))
   self.assertTrue(all(abs(utc-o)>=timedelta(minutes=10) for o in occupied));occupied.append(utc)
  for day in {d.date() for d in occupied}:self.assertLessEqual(sum(d.date()==day for d in occupied),30)
 def test_full_day_waits_for_next_allowed_window(self):
  policy={'window_start':'08:30','window_end':'11:30','weekdays':[0,1,2,3,4],'daily_limit':1,'hourly_limit':6}
  now=datetime(2026,9,15,6,tzinfo=timezone.utc)
  occupied=[datetime(2026,9,15,8,47,tzinfo=timezone.utc)]
  r=recommend_send({'timezone':'Europe/London'},'person',now,policy,occupied)
  self.assertTrue(r['recommended_send_local'].startswith('2026-09-16'))
 def test_resume_claim_is_blocked_in_both_word_orders(self):
  for body in ['I attached my resume for context.','My resume is attached for context.']:
   ctx={'email':'a@example.test','email_status':'verified','timezone':'Europe/London','facts_supported':True,'factual_review_hash':fingerprint('Test',body)}
   self.assertIn('resume',{b['code'] for b in blockers(ctx,'Test',body)})

if __name__=='__main__': unittest.main()
