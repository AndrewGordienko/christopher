import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from state import connect,register,get,sync_thread,decide,build_queue,projection,review_action,instant
from mission import plan_mission,validate_contact
from scheduling import resolve_timezone,recommend_send
from opportunities import payment_plan,contact_release
from subjects import rank_subjects
from research import validate_brief,read_sources,add_source,campaign,save_account
from apollo import normalize_contact,enrich_selected
from signals import add_pressure,ingest_jobs,classify_job
from test_workflow import brief
NOW=datetime(2026,9,14,22,0,tzinfo=timezone.utc)
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=connect(self.root/'state.sqlite3')
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def contact(self,pid='a',account='co',rank=1):
  return register(self.db,'test',account,pid,'technical_contract',account,{'name':pid,'email':pid+'@example.test','sender_mailbox':'me@example.test','timezone':'America/New_York','qualified':True,'email_status':'verified','body':'Hi there, one thought about simulation.','subject':'Possible project','rank':rank,'research_version':'r1','role':'Research Lead','company_type':'Research','facts_supported':True,'factual_review_hash':__import__('readiness').fingerprint('Possible project','Hi there, one thought about simulation.')},NOW)
 def snapshot(self,cid,messages=None,at=NOW):
  return {'account':'me@example.test','id':'thread-'+cid if messages else None,'complete':True,'source':'https://mail.google.com/mail/u/0/#search/test','tool_ref':'observed-test-fixture','observed_at':at.isoformat(),'subject':'Possible project','messages':messages or []}
 def sent(self,cid,date):return {'id':'m1','kind':'sent','sender':'me@example.test','recipients':[get(self.db,cid)['email']],'sent_at':date.isoformat(),'body':'Actual sent test fixture'}
 def test_mission_routes_and_counts(self):
  a=plan_mission('Find 30 organizations for technical contract work and the 3 best people at each')
  self.assertEqual((a['target_accounts'],a['people_per_account'],a['engine']),(30,3,'technical_contract'))
  b=plan_mission('Find 20 Canadian tire recycling facilities for Wapahki')
  self.assertEqual((b['engine'],b['subvertical'],b['unit']),('wapahki_facility','tire_recycling','facility'))
  c=plan_mission('Find OutageHub API buyers');self.assertEqual(c['objective'],'api_sales')
 def test_timezone_priority_unknown_dst(self):
  tz=resolve_timezone([{'source':'company_hq','source_id':'b','timezone':'Europe/London'},{'source':'apollo_person_location','source_id':'a','timezone':'America/New_York'}])
  self.assertEqual(tz['timezone'],'America/New_York');self.assertIsNone(resolve_timezone([])['timezone'])
  self.assertTrue(recommend_send(tz,'a',NOW)['recommended_send_local'].endswith('-04:00'))
  self.assertTrue(recommend_send(tz,'a',datetime(2026,11,2,12,tzinfo=timezone.utc))['recommended_send_local'].endswith('-05:00'))
  with self.assertRaises(ValueError):recommend_send(tz,'a',datetime(2026,9,14))
 def test_provider_verified_email_with_identity_conflict_is_blocked(self):
  from mission import review_campaign
  path=campaign('identity-test',root=self.root)
  add_source(path,{'id':'s1','url':'https://example.test/factory','observed_at':NOW.isoformat(),'tool':'test fixture','tool_ref':'fixture','text':'Test Company has a sorting robot. Kim manages automation.'})
  folder=save_account(path,brief());person=folder/'kim';person.mkdir()
  response={'person':{'name':'Kim','email':'shared@example.test','email_status':'verified'}}
  add_source(path,{'id':'apollo-test','url':'https://api.apollo.io/api/v1/people/match','observed_at':NOW.isoformat(),'tool':'Apollo API','tool_ref':'synthetic-fixture','text':json.dumps(response)})
  (person/'contact.json').write_text(json.dumps({'person_id':'kim','name':'Kim','source_id':'apollo-test','email':'shared@example.test','email_status':'verified','email_usable':False}))
  result=review_campaign(path);contact=result['accounts'][0]['contacts'][0]
  self.assertEqual(contact['provider_email_status'],'verified')
  self.assertEqual(contact['email_status'],'identity_unresolved')
  self.assertEqual(result['counts']['verified_emails'],0)
  self.assertTrue(any(b['code']=='email' for b in contact['blockers']))
  wrong={'person_id':'kim','name':'Kim','source_id':'apollo-test','email':'another@example.test','email_status':'verified'}
  (person/'contact.json').write_text(json.dumps(wrong))
  result=review_campaign(path);contact=result['accounts'][0]['contacts'][0]
  self.assertIsNone(contact['email']);self.assertEqual(contact['email_status'],'identity_unresolved')
  self.assertTrue(any(b['code']=='contact_identity' for b in contact['blockers']))
  # An older queue snapshot must not erase a newly detected identity problem.
  from mission import merge_queue_view
  merge_queue_view(contact,{'touch_number':1,'subject':contact['subject'],'body':contact['body'],'status':'review','send_at':None,'approval_hash':'old','sender_mailbox':'me@example.test','labels':[],'attachment_filenames':[],'blockers':[]})
  self.assertIsNone(contact['approval_hash']);self.assertTrue(any(b['code']=='contact_identity' for b in contact['blockers']))
 def test_shared_capacity_dedup_and_backup_hold(self):
  for name,account,rank in [('a','co',1),('b','co',2),('c','other',1),('d','third',1)]:
   cid=self.contact(name,account,rank);sync_thread(self.db,cid,self.snapshot(cid))
  q=build_queue(self.db,'2026-09-15',2,NOW)
  self.assertEqual(len(q['actions']),2);self.assertFalse(any(x['contact_id'].endswith('/b')for x in q['actions']))
  again=build_queue(self.db,'2026-09-15',2,NOW);self.assertEqual(q['actions'],again['actions'])
 def test_stale_sync_holds_queue(self):
  cid=self.contact();sync_thread(self.db,cid,self.snapshot(cid,at=NOW-timedelta(days=2)))
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
 def test_company_reply_pause_crosses_facilities_and_survives_import(self):
  from test_cell_qualification import qualified_context
  a=self.contact('a','north');b=self.contact('b','south');backup=self.contact('c','north',2)
  for cid in (a,b,backup):
   c=get(self.db,cid);ctx=json.loads(c['context']);ctx.update(parent_company_key='parent.test',pause_on_any_reply=True,primary_only=True)
   ctx.update(qualified_context(c['account_id'],ctx['subject'],ctx['body'],c['person_id']))
   register(self.db,'test',c['account_id'],c['person_id'],'wapahki_facility',c['account_id'],ctx,NOW)
   sync_thread(self.db,cid,self.snapshot(cid))
  self.assertEqual(len(build_queue(self.db,'2026-09-15',30,NOW)['actions']),1)
  reply={'id':'r1','kind':'out_of_office','sender':get(self.db,a)['email'],'sent_at':NOW.isoformat(),'body':'Away'}
  sync_thread(self.db,a,self.snapshot(a,[self.sent(a,NOW-timedelta(days=4)),reply]))
  c=get(self.db,b);register(self.db,'test','south','b','wapahki_facility','south',json.loads(c['context']),NOW)
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
  self.assertTrue(self.db.execute("SELECT 1 FROM settings WHERE key='company_pause:parent.test'").fetchone())
 def test_reply_cancels_all_future_sends_and_is_idempotent(self):
  cid=self.contact();sent=self.sent(cid,NOW-timedelta(days=4));snap=self.snapshot(cid,[sent]);sync_thread(self.db,cid,snap)
  decide(self.db,cid,{'action':'SEND','reason':'Relevant evaluation clarification','new_reason':'Clarify AIS artifacts','snapshot_at':get(self.db,cid)['snapshot_at'],'research_version':'r1','research_checked_at':NOW.isoformat(),'critic_passed':True,'body':'One thought was to distinguish AIS artifacts from unusual behaviour.'},NOW)
  q=build_queue(self.db,'2026-09-15',30,NOW);self.assertEqual(q['followups'],1)
  reply={'id':'r1','kind':'human','outcome':'technical_answer','sender':'a@example.test','sent_at':NOW.isoformat(),'body':'Yes, this is useful.'}
  snap['messages'].append(reply);sync_thread(self.db,cid,snap);sync_thread(self.db,cid,snap)
  self.assertEqual(get(self.db,cid)['status'],'REPLIED');self.assertEqual(projection(self.db)['queue'],[])
  self.assertEqual(get(self.db,cid)['recommended_action'],'REVIEW_REPLY');self.assertEqual(get(self.db,cid)['next_action_at'],NOW.isoformat())
  self.assertEqual(sum(m['useful_replies']for m in projection(self.db)['metrics']),1)
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
 def test_orphaned_active_relationship_is_visible(self):
  cid=self.contact();self.assertEqual(projection(self.db)['orphaned_relationships'][0]['id'],cid)
  self.db.execute('UPDATE contacts SET next_action_at=? WHERE id=?',(NOW.isoformat(),cid))
  self.assertEqual(projection(self.db)['orphaned_relationships'],[])
 def test_any_reply_includes_automatic_and_known_company_coworker(self):
  for kind,sender in [('automatic','a@example.test'),('human','colleague@example.test')]:
   with self.subTest(kind=kind):
    cid=self.contact('a',kind);c=get(self.db,cid);ctx=json.loads(c['context'])
    ctx.update(parent_company_key=kind,pause_on_any_reply=True,company_domains=['example.test'])
    register(self.db,'test',kind,'a','wapahki_facility',kind,ctx,NOW)
    bad={'id':'unrelated','kind':'human','sender':'colleague@unrelated.test','sent_at':NOW.isoformat(),'body':'Unrelated'}
    with self.assertRaises(ValueError):sync_thread(self.db,cid,self.snapshot(cid,[bad]))
    reply={'id':'r1','kind':kind,'sender':sender,'sent_at':NOW.isoformat(),'body':'Observed reply fixture'}
    sync_thread(self.db,cid,self.snapshot(cid,[reply]))
    row=self.db.execute('SELECT value FROM settings WHERE key=?',('company_pause:'+kind,)).fetchone()
    self.assertIn(sender,json.loads(row['value'])['reason'])
 def test_ooo_defers_and_survives_resync(self):
  cid=self.contact();m=self.sent(cid,NOW-timedelta(days=4));ooo={'id':'ooo','kind':'out_of_office','sender':'a@example.test','sent_at':NOW.isoformat(),'return_at':(NOW+timedelta(days=10)).isoformat(),'body':'Away until next week'}
  snap=self.snapshot(cid,[m,ooo]);sync_thread(self.db,cid,snap);expected=get(self.db,cid)['next_action_at'];sync_thread(self.db,cid,snap)
  self.assertEqual(get(self.db,cid)['next_action_at'],expected);self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
 def test_bounce_optout_decline_terminal(self):
  for i,kind in enumerate(['bounce','unsubscribe','declined']):
   cid=self.contact(str(i),str(i));m=self.sent(cid,NOW-timedelta(days=3));r={'id':'reply','kind':kind if kind!='declined' else 'human','outcome':kind,'sender':get(self.db,cid)['email'],'sent_at':NOW.isoformat(),'body':'test'}
   sync_thread(self.db,cid,self.snapshot(cid,[m,r]));self.assertIn(get(self.db,cid)['status'],{'BOUNCED','UNSUBSCRIBED','DECLINED'})
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
 def test_no_thread_switch_no_missing_capture(self):
  cid=self.contact();sync_thread(self.db,cid,self.snapshot(cid,[self.sent(cid,NOW-timedelta(days=4))]))
  with self.assertRaises(ValueError):sync_thread(self.db,cid,self.snapshot(cid))
  bad=self.snapshot(cid,[self.sent(cid,NOW-timedelta(days=4))]);bad['id']='different'
  with self.assertRaises(ValueError):sync_thread(self.db,cid,bad)
 def test_dynamic_followup_requires_reason_critic_research(self):
  cid=self.contact();sync_thread(self.db,cid,self.snapshot(cid,[self.sent(cid,NOW-timedelta(days=4))]))
  for value in [{'action':'SEND','reason':'bump'},{'action':'SEND','reason':'bump','snapshot_at':get(self.db,cid)['snapshot_at'],'research_version':'r1','new_reason':'something','critic_passed':True,'research_checked_at':NOW.isoformat(),'body':'I guarantee positive results quickly.'}]:
   with self.assertRaises(ValueError):decide(self.db,cid,value,NOW)
  self.assertEqual(build_queue(self.db,'2026-09-15',30,NOW)['actions'],[])
 def test_explicit_short_bump_does_not_need_invented_new_information(self):
  cid=self.contact();sync_thread(self.db,cid,self.snapshot(cid,[self.sent(cid,NOW-timedelta(days=4))]))
  value={'action':'SEND','reason':'No new evidence; a short reminder of the original question is appropriate.','snapshot_at':get(self.db,cid)['snapshot_at'],'research_version':'r1','followup_level':'bump','critic_passed':True,'research_checked_at':NOW.isoformat(),'body':'Hi A,\n\nJust following up on the missing-sensor question in case it got buried. Does that gap actually change the recovery decision in practice?\n\nBest,\nAndrew'}
  self.assertEqual(decide(self.db,cid,value,NOW)['recommended_action'],'SEND')
 def test_approval_never_sends_and_changed_copy_loses_approval(self):
  cid=self.contact();sync_thread(self.db,cid,self.snapshot(cid));build_queue(self.db,'2026-09-15',30,NOW)
  q=projection(self.db)['queue'][0];sid=q['id']
  context=json.loads(get(self.db,cid)['context'])
  context['final_checks']={'draft_hash':__import__('readiness').fingerprint(context['subject'],context['body']),'reviewed_at':NOW.isoformat(),'reviewer':'synthetic fixture',**{k:{'passed':True} for k in ('facts','grammar','voice')}}
  context.update(timezone_source='person_location',timezone_source_id='synthetic-fixture')
  self.db.execute('UPDATE contacts SET context=? WHERE id=?',(json.dumps(context),cid));self.db.commit()
  with patch('execution.mailbox_policy',return_value={'sender_mailbox':'me@example.test'}):
   self.assertFalse(review_action(self.db,sid,'approved',q['approval_hash'],NOW)['send_authorized'])
  self.assertEqual(get(self.db,cid)['touch_number'],0)
  with self.assertRaises(ValueError):review_action(self.db,sid,'sent')
 def test_payment_and_backup(self):
  self.assertEqual([p['amount']for p in payment_plan(7500)],['3750.00','3750.00'])
  self.assertEqual(len(payment_plan(2000)),1);self.assertEqual(len(payment_plan(12000)),3)
  with self.assertRaises(ValueError):payment_plan(float('nan'))
  self.assertEqual(contact_release(2,[{'rank':1,'outcome':{'type':'not_sent'}}],NOW)['status'],'held_backup')
 def test_apollo_identity_and_verification_bound_to_person(self):
  expected={'id':'a','name':'Person A','role':'Scientist'}
  raw={'id':'ap','name':'Person A','title':'Old role','email':'a@example.test','email_status':'verified','organization':{'primary_domain':'example.test'}}
  norm=normalize_contact(raw,expected,'example.test','s1',NOW.isoformat());self.assertEqual(norm['role'],'Scientist')
  source={'s1':{'tool':'Apollo API','text':json.dumps({'person':{**raw,'email_status':'unverified'}})}}
  with self.assertRaises(ValueError):validate_contact(norm,source,expected)
  with self.assertRaises(ValueError):normalize_contact(raw,expected,'wrong.test','s1',NOW.isoformat())
 def test_subject_hard_bans_no_fake_thread(self):
  cand=[{'id':'a','subject':'Re: Quick question'},{'id':'b','subject':'Possible project'}];critic={x['id']:{'facts_supported':True,'plain_language':True,'context_fit':True,'no_fake_personalization':True,'voice_fit':4,'recipient_fit':4,'body_fit':4}for x in cand}
  r=rank_subjects(cand,{},critic);self.assertFalse(r[0]['eligible']);self.assertTrue(r[1]['eligible'])
 def sources(self):
  path=campaign('test','test',self.root);add_source(path,{'id':'s1','url':'https://example.test','observed_at':NOW.isoformat(),'tool':'fixture','tool_ref':'fixture','text':'Test Company has a sorting robot. Kim manages automation. Producers must recover materials. https://jobs.example.test'});return path
 def test_facilities_not_collapsed_by_parent(self):
  path=self.sources();b=brief();b['engine']='wapahki_facility'
  b['facility']={'id':'north','name':'North plant','location':'Ontario','subvertical':'tire_recycling','fact_ids':['f1'],'automation':[{'process':'plc_hmi','fact_ids':['f1']}]}
  with self.assertRaises(ValueError):save_account(path,b)
  b['facts'][0]['entity_id']='north';one=save_account(path,b);b['facility']['id']='south';b['facts'][0]['entity_id']='south';two=save_account(path,b);self.assertNotEqual(one,two)
 def test_outagehub_requires_specific_gap_and_competitive_check(self):
  path=self.sources();b=brief();b['engine']='outagehub_api'
  with self.assertRaises(ValueError):save_account(path,b)
  b['grid_data_gap']={'existing_product':'NOC','current_observability':'heartbeat','event_changes_workflow':'Correlate cluster outage before dispatch','incremental_information':'utility state','buyer_function':'NOC','basis':['f1'],'equivalent_internal_visibility':False}
  with self.assertRaises(ValueError):save_account(path,b)
 def test_pressure_legal_owner_guard(self):
  path=self.sources();v={'type':'regulation','observed_fact':'Producer obligation','owner':'Producers','inference':'May affect processor demand','evidence':{'source_id':'s1','quote':'Producers must recover materials.'},'should_mention_in_email':True}
  with self.assertRaises(ValueError):add_pressure(self.db,path,'co',v)
  v.update(jurisdiction='Ontario',legal_obligation_owner='Producers')
  with self.assertRaises(ValueError):add_pressure(self.db,path,'co',v)
  v['should_mention_in_email']=False;self.assertTrue(add_pressure(self.db,path,'co',v))
 def test_ats_diff_failed_scan_not_empty_and_budget_not_invented(self):
  path=self.sources();capture={'observed_at':NOW.isoformat(),'result':{'provider':'greenhouse','jobs':[{'id':'1','url':'https://jobs.example.test/1','title':'Planning engineer','description':'Build simulation and planning tools.'}]},'capture':[{'url':'https://jobs.example.test','text':'Build simulation and planning tools.','observed_at':NOW.isoformat()}]}
  self.assertEqual(ingest_jobs(self.db,path,'co',capture,'s1')['new'],1)
  self.assertEqual(ingest_jobs(self.db,path,'co',capture,'s1')['unchanged'],1)
  with self.assertRaises(ValueError):ingest_jobs(self.db,path,'co',{'result':{'error':'network'}},'s1')
  sid=self.db.execute('SELECT id FROM signals').fetchone()['id']
  v={'technical_priorities':['planning'],'likely_owner':'Head of Research','evidence_quotes':['Build simulation and planning tools.'],**{k:.8 for k in ['technical_overlap','mission_interest','active_problem','bounded_project','ability_to_pay']},'external_contract_budget':'high'}
  with self.assertRaises(ValueError):classify_job(self.db,sid,v)
  v['external_contract_budget']='unknown';self.assertLess(classify_job(self.db,sid,v)['priority_signal'],.2)
if __name__=='__main__':unittest.main()
