import sys,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from state import connect,register,get,sync_thread,build_queue
from manual_sent import record
from daily_calendar import projection,change_plan,sent_evidence,add_business_days,day_at
NOW=datetime(2026,9,15,14,tzinfo=timezone.utc)
class DailyCalendarTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=connect(Path(self.tmp.name)/'db.sqlite3');self.cid=self.contact('one','a')
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def contact(self,account,person,rank=1):
  return register(self.db,'test',account,person,'technical_contract',account,{'name':person,'email':person+'@example.test','rank':rank,'sender_mailbox':'me@example.test','timezone':'America/New_York','qualified':True,'email_status':'verified','subject':'Question','body':'Draft','research_version':'r1'},NOW)
 def sync(self,cid=None,at=NOW,messages=None):
  cid=cid or self.cid
  s={'id':'thread-'+cid,'account':'me@example.test','source':'https://mail.google.com/mail/u/0/#sent','complete':True,'tool_ref':'fixture','observed_at':NOW.isoformat(),'subject':'Actual sent subject','messages':messages or [{'id':'sent-'+cid,'kind':'sent','sent_at':at.isoformat(),'sender':'me@example.test','recipients':[get(self.db,cid)['email']],'body':'Actual Gmail copy'}]}
  return sync_thread(self.db,cid,s)
 def test_manual_and_gmail_are_one_send_on_verified_day(self):
  record(self.db,self.cid,'Draft','Draft','me@example.test','a@example.test',(NOW-timedelta(days=1)).isoformat(),'manual',now=NOW)
  self.sync();rows=projection(self.db,now=NOW)['entries'];sent=[x for x in rows if x['kind']=='sent']
  self.assertEqual(len(sent),1);self.assertEqual(sent[0]['day'],'2026-09-15');self.assertEqual(sent[0]['body'],'Actual Gmail copy');self.assertFalse(sent[0]['accepted_example'])
 def test_followup_is_one_persisted_review_not_precomposed_send(self):
  self.sync();self.contact('one','b',2)
  p=projection(self.db,now=NOW);reviews=[x for x in p['entries'] if x['kind']=='followup_review']
  self.assertEqual(len(reviews),1);self.assertEqual(reviews[0]['day'],'2026-09-18');self.assertIsNone(reviews[0]['at']);self.assertFalse(reviews[0]['send_eligible']);self.assertNotIn('body',reviews[0]);self.assertEqual(len(reviews[0]['choices']),2)
  again=projection(self.db,now=NOW+timedelta(minutes=2));self.assertEqual([x['version'] for x in again['entries'] if x['kind']=='followup_review'],[reviews[0]['version']])
 def test_requested_future_draft_is_visible_without_send_decision_or_queue(self):
  from daily_calendar import prepare_followup
  self.sync();c=get(self.db,self.cid)
  draft={'subject':c['original_subject'],'body':'Could we start with one recorded failure?','thread_id':c['thread_id'],'review_on':'2026-09-18','send_at':'2026-09-18T14:10:00+00:00','path':'campaigns/test/followups/touch-2/draft.json'}
  prepare_followup(self.db,self.cid,draft,NOW)
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  self.assertEqual(r['planned_draft']['body'],draft['body']);self.assertFalse(r['send_eligible']);self.assertTrue(r['needs_refresh'])
  self.assertIsNone(get(self.db,self.cid)['decision'])
  queue=self.db.execute('SELECT * FROM scheduled_sends WHERE contact_id=?',(self.cid,)).fetchone()
  self.assertEqual(queue['status'],'waiting');self.assertIsNone(queue['send_at']);self.assertIsNone(queue['body'])
  with self.assertRaisesRegex(ValueError,'thread and subject'):prepare_followup(self.db,self.cid,{**draft,'thread_id':'different-thread'},NOW)
  msgs=json.loads(c['snapshot'])['messages'];msgs.append({'id':'reply','kind':'human','sender':'a@example.test','sent_at':NOW.isoformat(),'body':'Please wait'})
  self.sync(messages=msgs)
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='reply_review')
  self.assertIsNone(r['planned_draft'])
 def test_changing_the_next_action_removes_the_prepared_draft(self):
  from daily_calendar import prepare_followup
  self.sync();c=get(self.db,self.cid)
  prepare_followup(self.db,self.cid,{'subject':c['original_subject'],'body':'One question','thread_id':c['thread_id'],'review_on':'2026-09-18','path':'draft.json'},NOW)
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  change_plan(self.db,{'account_key':r['account_key'],'version':r['version'],'action':'WAIT','review_on':'2026-09-21','brief':'Give it more time','reason':'Changed plan'},NOW+timedelta(minutes=1))
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  self.assertIsNone(r['planned_draft'])
 def test_capacity_includes_actual_sends(self):
  self.sync();other=self.contact('two','b')
  sync_thread(self.db,other,{'id':None,'account':'me@example.test','source':'https://mail.google.com/mail/u/0/#search','tool_ref':'fixture','complete':True,'observed_at':NOW.isoformat(),'messages':[]})
  q=build_queue(self.db,'2026-09-15',1,NOW)
  self.assertEqual(q['sent'],1);self.assertEqual(q['actions'],[]);self.assertEqual(q['remaining_capacity'],0)
 def test_reply_pauses_account_and_overrides_followup(self):
  self.sync();projection(self.db,now=NOW)
  msgs=json.loads(get(self.db,self.cid)['snapshot'])['messages'];msgs.append({'id':'reply','kind':'human','sender':'a@example.test','sent_at':NOW.isoformat(),'body':'Let us talk'})
  self.sync(messages=msgs)
  review=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='reply_review')
  self.assertEqual(review['status'],'paused');self.assertEqual(review['action'],'WAIT')
 def test_saved_next_action_survives_refresh_and_rejects_stale_edit(self):
  self.sync();r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  v={'account_key':r['account_key'],'version':r['version'],'action':'WAIT','review_on':'2026-09-21','brief':'Wait for the current contact','reason':'Allow additional time'}
  change_plan(self.db,v,NOW+timedelta(minutes=1));r2=next(x for x in projection(self.db,now=NOW+timedelta(minutes=2))['entries'] if x['kind']=='followup_review');self.assertEqual(r2['day'],'2026-09-21');self.assertEqual(r2['action'],'WAIT')
  with self.assertRaisesRegex(ValueError,'account changed'):change_plan(self.db,v,NOW+timedelta(minutes=3))
 def test_different_account_and_unverified_backup_rejected(self):
  self.sync();other=self.contact('two','b');r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  v={'account_key':r['account_key'],'version':r['version'],'action':'CONTACT_NEXT_PERSON','contact_id':other,'review_on':'2026-09-21','brief':'Route question','reason':'Closer owner'}
  with self.assertRaisesRegex(ValueError,'same account|this account'):change_plan(self.db,v,NOW)
  backup=self.contact('one','c',2);self.db.execute("UPDATE contacts SET context=json_set(context,'$.email_status','unknown') WHERE id=?",(backup,));self.db.commit();v['contact_id']=backup
  with self.assertRaisesRegex(ValueError,'verify'):change_plan(self.db,v,NOW)
 def test_weekends_and_dst_dates(self):
  self.assertEqual(add_business_days('2026-09-18',3),'2026-09-23')
  self.assertEqual(day_at('2026-09-14T23:30:00+00:00'),'2026-09-15')
  self.assertEqual(day_at('2026-12-14T23:30:00+00:00'),'2026-12-14')

 def test_calendar_capacity_is_used_by_queue_builder(self):
  self.sync();change_plan(self.db,{'operation':'capacity','engine':'all','day':'2026-09-15','capacity':1},NOW)
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['capacity'],1)
 def test_two_real_sends_are_not_collapsed_as_manual_duplicates(self):
  self.sync();c=get(self.db,self.cid)
  self.db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(self.cid,'second-actual-message','sent',NOW.isoformat(),1,None));self.db.commit()
  self.assertEqual(len(sent_evidence(self.db)),2)
 def test_next_person_preserves_sent_anchor_and_waiting_eligibility(self):
  self.sync();backup=self.contact('one','b',2)
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  change_plan(self.db,{'account_key':r['account_key'],'version':r['version'],'action':'CONTACT_NEXT_PERSON','contact_id':backup,'review_on':'2026-09-21','brief':'Ask the closer owner','reason':'Team ownership clarified'},NOW+timedelta(minutes=1))
  again=next(x for x in projection(self.db,now=NOW+timedelta(minutes=2))['entries'] if x['kind']=='followup_review')
  self.assertEqual(again['contact_id'],self.cid);self.assertEqual(again['target_contact_id'],backup);self.assertEqual(again['last_sent_body'],'Actual Gmail copy')
  q=self.db.execute('SELECT * FROM scheduled_sends WHERE contact_id=? AND touch_number=2',(self.cid,)).fetchone()
  self.assertEqual(q['status'],'waiting');self.assertIsNone(q['body']);self.assertIsNone(q['send_at'])
 def test_close_sequence_pauses_backup_contacts(self):
  from state import eligible
  self.sync();backup=self.contact('one','b',2)
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  change_plan(self.db,{'account_key':r['account_key'],'version':r['version'],'action':'COMPLETE','review_on':'2026-09-15','brief':'Close this account','reason':'Andrew closed this sequence'},NOW+timedelta(minutes=1))
  ok,why=eligible(self.db,get(self.db,backup),NOW)
  self.assertFalse(ok);self.assertIn('Company paused',why)

 def test_linkedin_review_uses_selected_person_without_scheduling_or_consuming_capacity(self):
  self.sync(at=NOW-timedelta(minutes=5));second=self.contact('one','b',2);self.sync(second)
  ctx=json.loads(get(self.db,self.cid)['context']);ctx['linkedin_profile']={'url':'https://www.linkedin.com/in/example','source':'Apollo','source_id':'source-1'}
  self.db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(ctx),self.cid));self.db.commit()
  r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  change_plan(self.db,{'account_key':r['account_key'],'version':r['version'],'action':'LINKEDIN_REVIEW','contact_id':self.cid,'review_on':'2026-09-21','brief':'Check current role, then consider a connection','reason':'One account action after allowing time to reply'},NOW+timedelta(minutes=6))
  p=projection(self.db,now=NOW+timedelta(minutes=7));review=next(x for x in p['entries'] if x['kind']=='linkedin_review')
  self.assertEqual(review['target_contact_id'],self.cid);self.assertEqual(review['linkedin_profile']['source_id'],'source-1');self.assertFalse(review['send_eligible'])
  self.assertFalse(any(x['kind']=='outbound' for x in p['entries']))
  from state import eligible
  for cid in [self.cid,second]:
   ok,reason=eligible(self.db,get(self.db,cid),NOW+timedelta(days=7))
   self.assertFalse(ok);self.assertIn('LinkedIn review',reason)
  self.assertEqual(len(sent_evidence(self.db)),2)
  self.assertIsNone(self.db.execute("SELECT send_at FROM scheduled_sends WHERE contact_id=? AND touch_number=2",(second,)).fetchone()[0])

 def test_linkedin_review_rejects_other_accounts_and_yields_to_human_reply(self):
  self.sync();other=self.contact('two','b');r=next(x for x in projection(self.db,now=NOW)['entries'] if x['kind']=='followup_review')
  v={'account_key':r['account_key'],'version':r['version'],'action':'LINKEDIN_REVIEW','contact_id':other,'review_on':'2026-09-21','brief':'Check profile','reason':'Relevant role'}
  with self.assertRaisesRegex(ValueError,'same account|this account'):change_plan(self.db,v,NOW)
  v['contact_id']=self.cid;change_plan(self.db,v,NOW+timedelta(minutes=1))
  msgs=json.loads(get(self.db,self.cid)['snapshot'])['messages'];msgs.append({'id':'reply','kind':'human','sender':'a@example.test','sent_at':NOW.isoformat(),'body':'Tell me more'})
  self.sync(messages=msgs);p=projection(self.db,now=NOW+timedelta(minutes=3))
  self.assertFalse(any(x['kind']=='linkedin_review' for x in p['entries']));self.assertTrue(any(x['kind']=='reply_review' for x in p['entries']))

 def test_untrusted_profile_url_is_not_rendered(self):
  from daily_calendar import linkedin_profile
  c=get(self.db,self.cid);ctx=json.loads(c['context']);ctx['linkedin_profile']={'url':'https://linkedin.com.evil.test/in/name'};c['context']=json.dumps(ctx)
  self.assertIsNone(linkedin_profile(c))
