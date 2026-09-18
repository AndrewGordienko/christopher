"""Synthetic fixtures test evidence boundaries, not any prospect's actual state."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from benchmarks import validate_benchmark,validate_value_case,recipient_altitude
from mission import plan_mission

def fixture():
 return {'schema_version':1,'status':'proposed','mode':'pilot','vertical':'recycling','adapter_id':'test-mrf-v1','adapter_status':'hypothesis','basis':['plant'],
  'existing_production_objective':{'status':'unconfirmed','public_measures':[{'kind':'design_capacity','description':'Fixture design capacity, not actual production','basis':['plant']}],'confirmed_kpis':[]},
  'production_unit':{'type':'tonne','status':'proposed','definition':'Net input mass','basis':['plant']},'task_success':{'status':'proposed','definition':'Accepted material'},
  'primary_wapahki_metric':{'id':'human_intervention_minutes_per_operating_hour','status':'proposed','definition':'Active person-minutes over predeclared exposure','phase':'observational_baseline'},
  'secondary':[{'id':'autonomous_recovery_rate','phase':'authorized_intervention'}],
  'plant_guardrails':[{'metric':'quality','status':'proposed','basis':['plant']}],
  'likely_failure_classes':[{'class':'jam','status':'hypothesis','basis':['plant']}],
  'data_sources':[{'description':'Alarm and sampled intervention observations','availability':'unknown'}],
  'baseline_plan':{'event_model_version':'recovery-v1',**{k:'Unresolved definition to agree'for k in ['exposure_definition','intervention_definition','downtime_definition','stability_criterion','comparison_plan']},'unknowns':['Clock alignment']},
  'readiness':{'status':'conversation_only','data_access_confirmed':False,'baseline_measured':False,'control_authorized':False},'outreach_question':'How is recovery time measured?'}

class BenchmarkTests(unittest.TestCase):
 def test_recipient_altitude_is_role_based_not_contact_rank(self):
  self.assertEqual(recipient_altitude('Vice President-Engineering and Sustainability','automation_controls'),'corporate_technical')
  self.assertEqual(recipient_altitude("Directeur d’Ingénierie",'corporate_technical'),'automation_controls')
  self.assertEqual(recipient_altitude('General Manager, Granby Enviro Connexions','corporate_technical'),'plant_operations')
  self.assertEqual(recipient_altitude('Deputy Director General','plant_operations'),'corporate_technical')
 def setUp(self):self.facts={'plant':{'entity_id':'site'},'parent':{'entity_id':'parent'}}
 def test_design_capacity_cannot_confirm_a_kpi_by_parent_scope(self):
  b=fixture();self.assertEqual(validate_benchmark(b,self.facts,'site')['existing_production_objective']['status'],'unconfirmed')
  b['existing_production_objective'].update(status='confirmed',confirmed_kpis=[{'metric':'throughput','basis':['parent']}])
  with self.assertRaises(ValueError):validate_benchmark(b,self.facts,'site')
 def test_observation_cannot_measure_autonomous_recovery(self):
  for primary in [True,False]:
   b=fixture()
   if primary:b['primary_wapahki_metric']['id']='autonomous_recovery_rate'
   else:b['secondary'][0]['phase']='observational_baseline'
   with self.assertRaises(ValueError):validate_benchmark(b,self.facts,'site')
 def test_access_cannot_be_inferred_from_research(self):
  b=fixture();b['readiness']['data_access_confirmed']=True
  with self.assertRaises(ValueError):validate_benchmark(b,self.facts,'site')
 def test_discovery_can_leave_unit_and_metric_unresolved(self):
  b=fixture();b.update(mode='discovery',vertical='food');b['production_unit'].update(type=None,status='unknown');b['primary_wapahki_metric'].update(id=None,status='unknown')
  validate_benchmark(b,self.facts,'site')
 def test_three_visits_to_one_company_do_not_prove_transfer(self):
  b=fixture();b.update(vertical='food',adapter_status='pilot_ready')
  b['promotion']={'observations':[{'observation_id':str(i),'company_id':'same','facility_id':str(i),'kind':'conversation','basis':['plant']}for i in range(3)],'consistent_pattern':True,'adapter_complete':True,'contradictions_resolved':True,'reason':'Synthetic pattern', 'answers':{k:{'answer':'Synthetic sourced answer','basis':['plant']} for k in ['pain_owner','buyer','telemetry','failure_taxonomy','success_metric','denominator','safe_recovery_actions','pilot_scope']}}
  with self.assertRaises(ValueError):validate_benchmark(b,self.facts,'site')
  for i,o in enumerate(b['promotion']['observations']):o['company_id']=str(i)
  validate_benchmark(b,self.facts,'site')
  del b['promotion']['answers']['buyer']
  with self.assertRaises(ValueError):validate_benchmark(b,self.facts,'site')
 def test_missions_separate_beachhead_and_new_vertical(self):
  self.assertEqual(plan_mission('Find Canadian recycling facilities for Wapahki')['wapahki_mode'],'pilot')
  p=plan_mission('Find food packaging plants for a Wapahki pilot')
  self.assertEqual(p['wapahki_mode'],'discovery')
  self.assertEqual(p['sender_mode'],'factory_learning')
  self.assertEqual(p['objective'],'workflow_conversation')
  self.assertEqual(p['eventual_objective'],'pilot')
  self.assertNotIn('wapahki_mode',plan_mission('Find Wapahki investors'))
 def test_unknown_customer_metric_is_a_candidate_not_a_fact(self):
  v={'status':'hypothesis','basis':['plant'],'business_metric':{'status':'unconfirmed','primary':'OEE'},'economic_link':{'hypothesis':True,'basis':['plant'],'chain':['jam','operator','possible lost time','customer measure']},**{k:'Synthetic proposal'for k in ['automation','failure_hypotheses','wapahki_metric','pilot_value_proposition','first_step','value_exchange','geography','data_rights']}}
  with self.assertRaises(ValueError):validate_value_case(v,self.facts,'site')
  v['business_metric'].update(primary=None,primary_candidate='OEE');validate_value_case(v,self.facts,'site')
if __name__=='__main__':unittest.main()
