import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from state import connect, register, get, sync_thread
from followup_drafts import prepare, projection, change, choose_primary
from daily_calendar import projection as calendar

NOW=datetime(2026,9,16,20,tzinfo=timezone.utc)

class FollowupDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.tmp.name)/'db.sqlite3')
        self.cid=self.contact('one')

    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def contact(self,person):
        cid=register(self.db,'test','company',person,'technical_contract','company',
          {'name':person,'email':person+'@example.test','rank':1,'sender_mailbox':'me@example.test',
           'timezone':'Europe/London','qualified':True,'email_status':'verified','subject':'Original','body':'First draft','research_version':'r1'},NOW)
        sync_thread(self.db,cid,{'id':'thread-'+person,'account':'me@example.test',
          'source':'https://mail.google.com/mail/u/0/#sent','tool_ref':'fixture','complete':True,
          'observed_at':NOW.isoformat(),'subject':'Original','messages':[{'id':'msg-'+person,'kind':'sent',
          'sent_at':(NOW-timedelta(days=1)).isoformat(),'sender':'me@example.test','recipients':[person+'@example.test'],'body':'Exact original'}]})
        return cid

    def draft(self,cid=None):
        c=get(self.db,cid or self.cid)
        return {'review_on':'2026-09-17','subject':'Original','body':'A complete follow-up.',
                'thread_id':c['thread_id'],'path':'campaigns/test/draft.md'}

    def test_keeps_every_requested_person_without_send_actions(self):
        other=self.contact('two')
        before=self.db.execute('SELECT COUNT(*) FROM scheduled_sends').fetchone()[0]
        for cid in [self.cid,other]:prepare(self.db,cid,self.draft(cid),NOW)
        choose_primary(self.db,self.cid,'2026-09-17','Owns the technical question',NOW)
        p=projection(self.db)
        self.assertEqual(len(p),2)
        self.assertEqual([d['status'] for d in p],['review','held'])
        self.assertEqual(p[0]['other_contacts'][0]['name'],'two')
        self.assertTrue(all(not d['send_eligible'] and not d['send_authorized'] for d in p))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM scheduled_sends').fetchone()[0],before)
        self.assertIsNone(get(self.db,self.cid)['decision'])
        self.assertEqual(json.loads(get(self.db,self.cid)['snapshot'])['messages'][0]['body'],'Exact original')
        entries=calendar(self.db,now=NOW)['entries']
        self.assertEqual(len([e for e in entries if e['kind']=='planned_email']),2)
        self.assertFalse(any(e['kind']=='followup_review' for e in entries))

    def test_switching_primary_holds_previous_person(self):
        other=self.contact('two')
        for cid in [self.cid,other]:prepare(self.db,cid,self.draft(cid),NOW)
        choose_primary(self.db,self.cid,'2026-09-17','Owns the model',NOW)
        choose_primary(self.db,other,'2026-09-17','Better owner found',NOW+timedelta(seconds=1))
        rows=projection(self.db)
        self.assertEqual([r['contact_id'] for r in rows if r['status']=='review'],[other])
        self.assertEqual(rows[0]['disposition'],'HOLD')
        self.assertEqual(rows[1]['disposition'],'PRIMARY FOLLOW-UP')

    def test_guaranteed_results_cannot_be_saved_as_current_draft(self):
        with self.assertRaisesRegex(ValueError,'Do not guarantee'):
            prepare(self.db,self.cid,{**self.draft(),'body':'I guarantee positive results quickly.'},NOW)
        self.assertEqual(projection(self.db),[])

    def test_latest_full_reference_saves_without_send_authorization(self):
        from followup_lint import current_reference
        body=current_reference()['body']
        prepare(self.db,self.cid,{**self.draft(),'body':body},NOW)
        choose_primary(self.db,self.cid,'2026-09-17','Owns the relevant work',NOW)
        row=projection(self.db)[0]
        self.assertEqual(row['body'],body)
        self.assertEqual(row['disposition'],'PRIMARY FOLLOW-UP')
        self.assertEqual(row['lint_issues'],[])
        self.assertFalse(row['send_authorized'])

    def test_reply_to_peer_holds_draft_and_keeps_text(self):
        other=self.contact('two');prepare(self.db,self.cid,self.draft(),NOW)
        self.db.execute("UPDATE contacts SET status='REPLIED',last_inbound_at=? WHERE id=?",(NOW.isoformat(),other));self.db.commit()
        d=projection(self.db)[0]
        self.assertEqual(d['status'],'held');self.assertIn('reply',d['hold_reason'])
        self.assertEqual(d['body'],'A complete follow-up.')

    def test_observed_gmail_schedule_holds_company_and_explains_local_revision(self):
        from state import company_key
        other=self.contact('two')
        prepare(self.db,self.cid,self.draft(),NOW)
        choose_primary(self.db,self.cid,'2026-09-17','Owns the model',NOW)
        observation={'contact_id':other,'name':'two','scheduled_display':'17 Sept 2026, 13:17',
                     'source':'https://mail.google.com/mail/u/0/#scheduled/thread-two'}
        reason='An existing follow-up to two is scheduled in Gmail; hold additional outreach.'
        self.db.execute('INSERT INTO settings VALUES(?,?)',('company_pause:'+company_key(get(self.db,self.cid)),
            json.dumps({'reason':reason,'external_followup':observation})));self.db.commit()
        row=projection(self.db)[0]
        self.assertEqual(row['status'],'held')
        self.assertEqual(row['why'],reason)
        self.assertEqual(row['external_schedule'],observation)
        self.assertEqual(row['body'],self.draft()['body'])
        with self.assertRaisesRegex(ValueError,'paused'):
            choose_primary(self.db,self.cid,'2026-09-17','Try again',NOW)

    def test_new_outbound_invalidates_previous_draft(self):
        prepare(self.db,self.cid,self.draft(),NOW)
        self.db.execute('UPDATE contacts SET touch_number=2,last_outbound_at=? WHERE id=?',(NOW.isoformat(),self.cid));self.db.commit()
        self.assertEqual(projection(self.db)[0]['status'],'held')

    def test_multiple_existing_gmail_schedules_resolve_to_each_contact(self):
        other=self.contact('two')
        for cid in [self.cid,other]:prepare(self.db,cid,self.draft(cid),NOW)
        observations=[{'contact_id':cid,'name':get(self.db,cid)['name'],
                       'source':'https://mail.google.com/mail/u/0/#scheduled/'+cid,
                       'body':'Exact selected message for '+cid} for cid in [self.cid,other]]
        self.db.execute('INSERT INTO settings VALUES(?,?)',('company_pause:company',json.dumps({
            'reason':'User scheduled both contacts in Gmail.',
            'external_followup':observations[0],'external_followups':observations})))
        self.db.commit()
        for row in projection(self.db):
            self.assertEqual(row['external_schedule']['contact_id'],row['contact_id'])
            self.assertEqual(row['body'],'A complete follow-up.')
            self.assertEqual(row['status'],'held')
            self.assertFalse(row['send_authorized'])

    def test_bad_thread_and_stale_hold_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'original thread'):prepare(self.db,self.cid,{**self.draft(),'thread_id':'wrong'},NOW)
        prepare(self.db,self.cid,self.draft(),NOW)
        row=projection(self.db)[0]
        value={'contact_id':self.cid,'review_on':row['day'],'version':row['updated_at'],'status':'held'}
        change(self.db,value,NOW+timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError,'changed'):change(self.db,value,NOW+timedelta(seconds=2))
        self.assertEqual(projection(self.db)[0]['status'],'held')
        with self.assertRaisesRegex(ValueError,'review or held'):change(self.db,{**value,'status':'approved'},NOW)

if __name__=='__main__':unittest.main()
