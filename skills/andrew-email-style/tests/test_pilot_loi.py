"""Synthetic customer evidence tests quality, signature and permission boundaries."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pilot_loi import field,validate,qualification,loi_quality,qualified_signed,render_brief,metrics,priority,QUALIFICATION,OWNERS,LOI_FIELDS,FACTORS
NOW=datetime(2026,9,14,tzinfo=timezone.utc)
TEXT='Synthetic signed pilot document for Fixture plant and Fixture company; confirmed customer discussion; exact fixture system, problem and responsibilities.'
SOURCES={'call':{'text':TEXT},'doc':{'text':TEXT},'public':{'text':TEXT}}
def evidence(source='call'):return [{'source_id':source,'quote':TEXT}]
def event(stage,day,kind='technical_call'):
 return {'stage':stage,'at':f'2026-09-{day:02}T10:00:00+00:00','kind':kind,'evidence':evidence('doc'if kind=='signed_document'else 'call'),'outcome':'positive'}
def fixture():
 return {'schema_version':1,'engine':'wapahki_facility','facility_id':'plant','company_id':'company','facility_name':'Fixture plant','company_name':'Fixture company','stage':'qualified','case_owner':'Andrew','next_action':'Align the proposed pilot brief','next_action_trigger':'After customer confirms scope',
  'qualification':{k:field('Synthetic '+k,'confirmed',evidence(),'technical_call')for k in QUALIFICATION},'owners':{k:field('Synthetic owner','confirmed',evidence(),'technical_call')for k in OWNERS},'discovery':{'failure_frequency':field(),'recovery_duration':field()},'scope':{},'milestones':[event('conversation',2),event('qualified',2)],'permissions':{},'loi':{'signature_status':'not_requested','fields':{},'document_source_ids':[]},'loi_priority':{'factors':{k:{'rating':None,'reason':'unknown','evidence':[]}for k in FACTORS}}}
def signed(v):
 v['stage']='loi_signed';v['milestones'] += [event('pilot_scoped',3),event('loi_sent',4,'sent_mail'),event('loi_signed',7,'signed_document')]
 v['loi']={'signature_status':'executed','signed_at':'2026-09-07T10:00:00+00:00','document_source_ids':['doc'],'signatories':['Synthetic authorized customer','Synthetic Wapahki signatory'],'signature_evidence':evidence('doc'),'fields':{k:field('Synthetic '+k,'confirmed',evidence('doc'),'signed_document')for k in LOI_FIELDS}}
 v['loi']['fields']['facility']['value']=v['facility_name']
 return v
class PilotLoiTests(unittest.TestCase):
 def test_unknown_quantitative_baseline_does_not_block_qualified_brief(self):
  v=fixture();validate(v,SOURCES,NOW);self.assertTrue(qualification(v)['ready_for_loi_ask']);self.assertIn('quantitative baseline',render_brief(v).lower())
 def test_title_alone_cannot_confirm_authority(self):
  v=fixture();v['owners']['pilot_signatory']['evidence_kind']='public_research'
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_positive_conversation_can_generate_provisional_brief_without_loi_ask(self):
  v=fixture();v['stage']='conversation';v['milestones']=v['milestones'][:1];v['qualification']['authorization_path']=field()
  validate(v,SOURCES,NOW);self.assertFalse(qualification(v)['ready_for_loi_ask']);self.assertIn('not yet qualified',render_brief(v))
  v['stage']='loi_sent';v['milestones'].append(event('loi_sent',4,'sent_mail'))
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_generic_signed_interest_is_c_not_qualified_loi(self):
  v=signed(fixture());v['loi']['fields']={};validate(v,SOURCES,NOW)
  self.assertEqual(loi_quality(v),'C');self.assertFalse(qualified_signed(v))
 def test_verbal_interest_and_unsigned_scope_are_not_signed(self):
  v=signed(fixture());v['loi']['signature_status']='draft'
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
  v=signed(fixture());v['milestones'][-1]['kind']='customer_reply'
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_signed_loi_does_not_grant_baseline_or_control_permission(self):
  v=signed(fixture());validate(v,SOURCES,NOW);self.assertTrue(qualified_signed(v))
  v['stage']='baseline';v['milestones'].append(event('baseline',9,'telemetry_observation'))
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
  v['milestones'].append(event('pilot_agreement',8,'signed_document'));v['pilot_agreement']={'signature_status':'executed','signature_evidence':evidence('doc')}
  v['permissions']['data']={'authorized':True,'scope':'Fixture bounded read-only','kind':'explicit_permission','evidence':evidence()};validate(v,SOURCES,NOW)
  v['stage']='closed_loop_recovery';v['milestones'].append(event('closed_loop_recovery',10,'deployment_observation'))
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_quality_is_document_scope_not_call_notes(self):
  v=signed(fixture());v['loi']['fields']['benchmark']['evidence']=evidence('call')
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
  v=signed(fixture());v['loi']['fields']['facility']['value']='Another plant'
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_cycles_report_open_cases_and_do_not_count_scheduled_contact(self):
  a=signed(fixture());a['first_contact_at']='2026-09-01T10:00:00+00:00'
  b=fixture();b['first_contact_at']='2026-09-01T10:00:00+00:00'
  c=fixture();c['first_contact_at']=None;c['scheduled_at']='2026-09-01T10:00:00+00:00'
  r=metrics([a,b,c],NOW);self.assertEqual(r['facilities_contacted'],2);self.assertEqual(r['qualified_signed_lois'],1)
  self.assertEqual(r['cycle_times']['first_contact_to_signed']['median_days'],6);self.assertEqual(r['cycle_times']['first_contact_to_signed']['open'],1)
  self.assertEqual(r['conversion']['signed_per_contacted']['denominator'],2)
  self.assertIsNone(metrics([],NOW)['cycle_times']['first_contact_to_signed']['median_days'])
  b['stage']='closed';r=metrics([b],NOW)['cycle_times']['first_contact_to_signed'];self.assertEqual(r['open'],0);self.assertEqual(r['closed_without_conversion'],1)
 def test_unknown_factors_are_not_probability_or_zero(self):
  r=priority(fixture());self.assertIsNone(r['ordinal_index']);self.assertIsNone(r['loi_probability']);self.assertEqual(r['assessed_dimensions'],0)
 def test_cannot_launder_qualification_through_history(self):
  v=fixture();v['stage']='research';v['qualification']['human_intervention']=field()
  with self.assertRaises(ValueError):validate(v,SOURCES,NOW)
 def test_recorded_positive_call_generates_brief_and_preserves_event_history(self):
  from state import connect
  from research import campaign,add_source,write_json
  from pilot_loi import save_case,load_case,project
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);path=campaign('fixture',root=root);folder=path/'accounts'/'plant';folder.mkdir(parents=True)
   write_json(folder/'research.json',{'facility':{'id':'plant'},'company':{'id':'company'}})
   add_source(path,{'id':'call','url':'https://example.test/call-note','observed_at':NOW.isoformat(),'tool':'synthetic customer call','tool_ref':'fixture','text':TEXT})
   with connect(root/'test.sqlite3')as db:
    r=save_case(db,path,'plant',fixture());self.assertTrue(r['brief_generated']);self.assertTrue((folder/'pilot-brief.md').exists());self.assertFalse(r['sending_enabled'])
    self.assertEqual(project(db)[0]['first_contact_at'],None)
    v=load_case(db,'fixture','plant');v['milestones'].append(event('site_visit',3));v['milestones'].pop(0)
    with self.assertRaises(ValueError):save_case(db,path,'plant',v)
if __name__=='__main__':unittest.main()
