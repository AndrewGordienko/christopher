import copy,json,tempfile,unittest,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from state import connect,register,sync_thread,build_queue,projection,review_action,get
from execution import action_record,digest,approved_record,claim,preflight,confirm
from gmail_labels import expected_labels,reconcile_plan,ROOT,STATUSES,ACTIONS,plan_thread,confirm as confirm_labels,pending
from readiness import fingerprint
from scheduling import recommend_send
NOW=datetime(2026,9,14,18,0,tzinfo=timezone.utc)
class ExecutionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=connect(Path(self.tmp.name)/'test.sqlite3')
  self.sender='gordienko.adg@gmail.com';self.subject='Possible project';self.body='Hi David,\n\nOne thought about simulation.\n\nBest,\nAndrew'
  self.cid=register(self.db,'test','gfw','david','technical_contract','gfw.test',{'name':'David','company_name':'GFW','email':'david@gfw.test','sender_mailbox':self.sender,'timezone':'America/Los_Angeles','qualified':True,'email_status':'verified','body':self.body,'subject':self.subject,'rank':1,'research_version':'r1','facts_supported':True,'factual_review_hash':fingerprint(self.subject,self.body)},NOW)
  ctx=json.loads(get(self.db,self.cid)['context'])
  ctx.update(timezone_source='person_location',timezone_source_id='fixture-location',final_checks={'draft_hash':fingerprint(self.subject,self.body),'reviewed_at':NOW.isoformat(),'reviewer':'test fixture','grammar':{'passed':True},'voice':{'passed':True},'facts':{'passed':True}})
  self.db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(ctx),self.cid));self.db.commit()
  sync_thread(self.db,self.cid,{'account':self.sender,'id':None,'complete':True,'source':'https://mail.google.com/mail/u/0/#search/test','tool_ref':'fixture','observed_at':NOW.isoformat(),'messages':[]})
  build_queue(self.db,'2026-09-15',30,NOW);self.q=projection(self.db)['queue'][0]
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def approve(self):
  context=json.loads(get(self.db,self.cid)['context'])
  context['final_checks']={'draft_hash':fingerprint(self.subject,self.body),'reviewed_at':NOW.isoformat(),'reviewer':'synthetic fixture',**{k:{'passed':True} for k in ('facts','grammar','voice')}}
  context.update(timezone_source='person_location',timezone_source_id='synthetic-fixture')
  self.db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(context),self.cid));self.db.commit()
  review_action(self.db,self.q['id'],'approved',self.q['approval_hash'],NOW)
 def observation(self):
  r=action_record(self.db,self.q['id'])
  return {k:r[k] for k in ('sender_mailbox','recipient','subject','body','cc','bcc','labels')}|{'attachment_filenames':[],'scheduled_at':r['send_at'],'source':'https://mail.google.com/mail/u/0/#scheduled/real-observed-test-id','tool_ref':'fixture','observed_at':NOW.isoformat(),'thread_id':'test-thread','folder':'Scheduled'}
 def test_unapproved_and_changed_fields_cannot_execute(self):
  with self.assertRaises(ValueError):claim(self.db,self.q['id'],self.q['approval_hash'],NOW)
  self.approve()
  for column,value in [('send_at','2026-09-15T23:00:00+00:00'),('subject','Changed')]:
   old=self.db.execute('SELECT '+column+' FROM scheduled_sends WHERE id=?',(self.q['id'],)).fetchone()[0]
   self.db.execute('UPDATE scheduled_sends SET '+column+'=? WHERE id=?',(value,self.q['id']));self.db.commit()
   with self.assertRaises(ValueError):approved_record(self.db,self.q['id'],NOW)
   self.db.execute('UPDATE scheduled_sends SET '+column+'=? WHERE id=?',(old,self.q['id']));self.db.commit()
 def test_approval_bound_to_display_and_gmail_receipt(self):
  with self.assertRaises(ValueError):review_action(self.db,self.q['id'],'approved','stale')
  self.approve();claim(self.db,self.q['id'],self.q['approval_hash'],NOW)
  with self.assertRaises(ValueError):claim(self.db,self.q['id'],self.q['approval_hash'],NOW)
  o=self.observation();bad=copy.deepcopy(o);bad['sender_mailbox']='wrong@example.test'
  with self.assertRaises(ValueError):preflight(self.db,self.q['id'],bad,NOW)
  bad=copy.deepcopy(o);bad['body']+='\nAutomatic signature'
  with self.assertRaises(ValueError):confirm(self.db,self.q['id'],bad,NOW)
  result=confirm(self.db,self.q['id'],o,NOW)
  self.assertEqual(result['status'],'gmail_scheduled');self.assertFalse(result['sent']);self.assertEqual(get(self.db,self.cid)['touch_number'],0)
 def test_rebuild_preserves_approved_time_and_copy(self):
  self.approve();before=action_record(self.db,self.q['id'])
  build_queue(self.db,'2026-09-15',30,NOW+timedelta(minutes=1))
  self.assertEqual(action_record(self.db,self.q['id']),before)
  self.assertEqual(self.db.execute('SELECT status FROM scheduled_sends WHERE id=?',(self.q['id'],)).fetchone()[0],'approved')
 def test_spacing_and_afternoon_uses_same_local_day(self):
  when=datetime(2026,9,14,18,0,tzinfo=timezone.utc)
  policy={'window_start':'08:30','window_end':'16:30','weekdays':[0,1,2,3,4],'minimum_lead_minutes':15,'minimum_spacing_minutes':10}
  first=recommend_send({'timezone':'America/New_York'},'a',when,policy=policy)
  t=datetime.fromisoformat(first['recommended_send_utc'].replace('Z','+00:00'))
  self.assertEqual(t.astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date(),when.date())
  second=recommend_send({'timezone':'America/New_York'},'a',when,policy=policy,occupied=[t])
  other=datetime.fromisoformat(second['recommended_send_utc'].replace('Z','+00:00'))
  self.assertGreaterEqual(abs(other-t),timedelta(minutes=10))
 def test_label_lifecycle_and_unrelated_labels_preserved(self):
  c=get(self.db,self.cid);c.update(status='AWAITING_REPLY',touch_number=1,last_outbound_at=NOW.isoformat(),next_action_at=(NOW-timedelta(days=1)).isoformat())
  labels=expected_labels(c,[],now=NOW);self.assertIn(STATUSES['Awaiting Reply'],labels);self.assertIn(ACTIONS['Follow-up Due'],labels)
  c.update(status='REPLIED',last_inbound_at=(NOW+timedelta(minutes=1)).isoformat(),reply_type='technical_answer')
  plan=reconcile_plan(c,[],labels+['Finance'],now=NOW)
  self.assertIn(STATUSES['Reply Needed'],plan['add']);self.assertIn(ACTIONS['Follow-up Due'],plan['remove']);self.assertEqual(plan['preserve'],['Finance'])
  c.update(status='UNSUBSCRIBED')
  labels=expected_labels(c,[],now=NOW);self.assertIn(STATUSES['Do Not Contact'],labels)
  self.assertEqual(len([x for x in labels if '/status/' in x]),1)
 def test_label_receipt_requires_actual_match_and_preserves_unrelated(self):
  self.db.execute('UPDATE contacts SET thread_id=?,touch_number=1,status=? WHERE id=?',('observed-thread','AWAITING_REPLY',self.cid));self.db.commit()
  p=plan_thread(self.db,self.cid,['Finance'],NOW)
  o={k:p[k] for k in ('mailbox','thread_id','expected_hash')}
  o.update(labels=p['desired']+['Finance'],previous_labels=['Finance'],observed_at=NOW.isoformat(),source='https://mail.google.com/mail/u/0/#inbox/observed-thread',tool_ref='fixture')
  wrong={**o,'labels':p['desired']}
  with self.assertRaises(ValueError):confirm_labels(self.db,self.cid,wrong,NOW)
  wrong={**o,'thread_id':'different'}
  with self.assertRaises(ValueError):confirm_labels(self.db,self.cid,wrong,NOW)
  self.assertEqual(confirm_labels(self.db,self.cid,o,NOW)['status'],'verified')
  self.assertEqual(pending(self.db,NOW),[])
  self.db.execute("UPDATE contacts SET status='UNSUBSCRIBED' WHERE id=?",(self.cid,))
  self.assertEqual(len(pending(self.db,NOW)),1)
 def test_opt_out_remains_suppressed_when_added_to_new_campaign(self):
  sync_thread(self.db,self.cid,{'account':self.sender,'id':'stop-thread','complete':True,'source':'https://mail.google.com/mail/u/0/#inbox/stop-thread','tool_ref':'fixture','observed_at':NOW.isoformat(),'messages':[{'id':'stop-message','sender':'david@gfw.test','kind':'reply','outcome':'unsubscribe','sent_at':NOW.isoformat()}]})
  cid=register(self.db,'new-campaign','gfw','david','technical_contract','gfw.test',json.loads(get(self.db,self.cid)['context']),NOW)
  self.assertEqual(get(self.db,cid)['status'],'UNSUBSCRIBED')
if __name__=='__main__':unittest.main()
