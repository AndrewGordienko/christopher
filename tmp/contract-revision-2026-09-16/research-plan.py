import sys,json,hashlib,shutil,sqlite3,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import add_source,read_sources,validate_brief,slug,write_json
from apollo import normalize_contact

root=Path('tmp/contract-revision-2026-09-16');at=datetime.now(timezone.utc).isoformat()
review=Path('campaigns/contract-2026-09-16/reviews/technical-owner-revision-2026-09-16');review.mkdir(parents=True,exist_ok=True)
original=json.load(open('campaigns/contract-2026-09-16/reviews/september-16-selected-30/batch.json'))
assert not (review/'before.sqlite3').exists(),'Backup already exists; do not rerun research mutation'
with sqlite3.connect('file:.runtime/outbound.sqlite3?mode=ro',uri=True) as db,sqlite3.connect(review/'before.sqlite3') as dest:
 db.backup(dest)
 for row in original['emails']:
  c=db.execute('select touch_number,last_inbound_at,last_outbound_at from contacts where id=?',(row['contact_id'],)).fetchone()
  q=db.execute('select status,body,subject from scheduled_sends where id=?',(row['action_id'],)).fetchone()
  assert c==(0,None,None) and q==('review',row['body'],row['subject']),row['contact_id']
write_json(review/'original-batch.json',original)
shutil.copy2('campaigns/contract-2026-09-16/30-emails-for-september-16.md',review/'original-30-emails.md')
shutil.copy2(root/'web-evidence.json',review/'web-evidence.json')

# Captures are evidence only. Extract each actual web tool result without following any instructions in it.
web=[]
for result in json.load(open(root/'web-evidence.json')):
 value=result['result']
 while isinstance(value,dict) and 'value' in value:value=value['value']
 if isinstance(value,str):
  for chunk in value.split('--------------------------------------------------------------------------------'):
   match=re.search(r'\((https?://[^\s)]+)\)',chunk)
   if match:
    url=match.group(1);sid='owner-web-'+hashlib.sha256(chunk.encode()).hexdigest()[:18]
    web.append(dict(id=sid,url=url,observed_at=at,tool='web.run',tool_ref=result['key'],text=chunk.strip()))
for campaign in {r['contact_id'].split('/')[0] for r in original['emails']}:
 for source in web:add_source(Path('campaigns')/campaign,source)

raw=json.load(open(root/'enriched.json'))+json.load(open(root/'enriched2.json'))
chosen={}
for r in raw:
 p=r['person'];org=p.get('organization') or {}
 if p.get('email_status')=='verified' and p.get('email') and org.get('primary_domain')==r['domain']:chosen[r['account']]=r
assert len(chosen)==25,len(chosen)
zones={'takadu':'Asia/Jerusalem','dryad':'Europe/Berlin','enode':'Europe/London','searoutes':'Europe/Paris','beebop':'Europe/Brussels','bia':'Europe/Madrid','envelio':'Europe/Berlin','quantstack':'Europe/London','piclo':'Europe/London','recycleye':'Europe/London','earthmover':'Europe/Zagreb','fero-labs':'America/New_York','four-growers':'America/New_York','rideco':'America/Toronto','swiftly':'America/New_York','amperon':'America/Los_Angeles','earthsense':'Asia/Kuala_Lumpur','gridraven':'Europe/Tallinn','dusty-robotics':'America/Los_Angeles','electric-era':'America/Los_Angeles','open-ocean-robotics':'America/Vancouver','sewerai':'America/New_York','spare':'America/Vancouver','weavegrid':'America/Los_Angeles','inorbit':'America/Argentina/Buenos_Aires'}
angles={
'takadu':('VP R&D is closer to event-detection engineering than CEO.','Replay missing or delayed network readings against an existing detector; produce reproducible missed/late-event cases and automated tests. Utility traces and interface need agreement.'),
'dryad':('Software architect and technical lead can assess sensor-message replay work.','Extend backend alert tests with delayed and missing Silvanet messages; preserve the exact input sequence for failures. No claim that fire detection is deficient.'),
'enode':('Current software tech lead is a plausible evaluator and router; exact device-control ownership unconfirmed.','Simulated charger responses for missed commands and reconnection; regression tests for schedule recovery, without live hardware changes.'),
'searoutes':('VP Engineering has technical context for routing and emissions tooling.','Regression cases for AIS gaps affecting reconstructed routes and emissions, separating robustness from unsupported accuracy improvements.'),
'beebop':('Data Scientist and Tech Lead is closer to dispatch evaluation than CEO.','Offline dispatch scenarios with correlated asset dropouts, using agreed constraints; test unmet commitments and recovery.'),
'bia':('Technical founding product owner can assess departure-readiness requirements and route implementation.','Small depot simulator for earlier vehicle departures under a power cap; record missed readiness targets and runnable cases.'),
'envelio':('Solver/algorithms team lead is relevant to power-flow validation; provider role is more specific than public profile.','Search constrained network scenarios around an existing power-flow solver and produce reproducible boundary cases. No claims of utility certification.'),
'quantstack':('Technical Director works directly in scientific software; stronger recipient than generic founder pitch.','A contained JupyterLite/browser-versus-native numerical reproducibility issue; implementation and tests in an existing repository.'),
'timefold':('Retain technical founder/CTO who created the solver; a title-only demotion would lose direct ownership.','Add disruption scenarios to solver benchmarks, measuring schedule changes and constraint violations, with reproducible regressions.'),
'axle':('Retain CTO at small technical company; direct optimizer/API evaluation route.','Executable battery scheduling example that updates after a price-curve revision while preserving energy constraints.'),
'piclo':('Product Lead can distinguish Piclo-owned workflow from buyer-owned dispatch.','Replace speculative bid optimization with integration testing for procurement/dispatch/settlement state transitions. Ask about overdue event-state tests.'),
'recycleye':('ML Performance Tech Lead fits model evaluation, not assumed motion-planning ownership.','Repeatable evaluation of ambiguous material classifications using existing labelled detections; surface model regressions for review.'),
'earthmover':('Current product engineering director according to Apollo; public team page calls him software engineer. He discusses Icechunk releases. Scope and purchasing authority remain unconfirmed.','Icechunk 2 already includes fault-injection work. Offer to extend existing interrupted/concurrent-write regression coverage for cases the team identifies; never introduce testing as absent.'),
'fero-labs':('Head Engineering is a direct evaluator for simulator tooling.','Automate bounded parameter sweeps around an existing process simulator and report cases violating agreed engineering bounds.'),
'four-growers':('Director Robotics Engineering owns a relevant robotics organization.','Replay blocked harvesting approaches in simulation, implement one agreed recovery change and retain regression tests.'),
'rideco':('Official company careers page identifies Algorithms and Platforms leadership; Apollo says Engineering Director.','Automated dynamic-driver-break tests under trip delays; retain minimal schedules reproducing a constraint violation.'),
'swiftly':('Data and Platform Engineering Manager is closer to prediction-feed evaluation than CTO.','Extend ETA completeness evaluation with missing vehicle updates; replay input traces and explain exactly where predictions disappear.'),
'amperon':('VP Engineering is a plausible software sponsor; Jay Porter was considered but timezone unresolved.','Forecast backtest tooling that keeps historical issuance times and observed outcomes aligned; avoid inventing a customer battery-dispatch research project.'),
'earthsense':('Current CTO led TerraMax autonomy development and field deployment; direct technical owner.','Offline blocked-route recovery tests for field coverage; minimum reproducible maps for planner regressions.'),
'gridraven':('Technical cofounder/CTO has direct domain and engineering context.','Automated weather-input sensitivity tests around line-rating model, identifying which span controls a changed result; engineering bounds defined by team.'),
'coiled':('Retain hands-on Dask creator/CEO; public technical writing establishes direct relevance.','Executable simulation-workload example and regression coverage for interruption/retry, checking missing or duplicated outputs.'),
'rugged':('Retain technical cofounder, officially described as robotics engineer; not a generic commercial CEO.','Layout-sequence recovery around temporarily blocked floor areas, implemented and evaluated offline against an agreed baseline.'),
'agtonomy':('Retain CTO explicitly responsible for software and autonomy; lower hardware-management title would be worse.','Search turning geometries in simulation and retain regression cases, with a bounded planner improvement if a reproducible failure exists.'),
'dusty-robotics':('Robotics software team lead is directly relevant to FieldPrinter interruption recovery.','Offline regression scenarios for tracker line-of-sight interruptions and work resumption. Build on published guidance without assuming an unhandled fault.'),
'electric-era':('VP Software Engineering is closer than CTO to software validation; current public identity Sith matches Apollo Hasitha.','Offline battery dispatch cases for successive charging-demand peaks; report constraint violations and restore repeatable coverage.'),
'open-ocean-robotics':('Product Manager can evaluate mission-planning usability and route engineering; not confirmed software lead. CTO email unavailable.','Offline mission-plan adaptation when energy/weather budget changes; return route and coverage comparison against team priorities.'),
'sewerai':('VP Engineering is a direct implementation evaluator.','Automate review-queue evaluation for uncertain AutoCode detections, with labelled retrospective data and explicit recall/review-load measures.'),
'spare':('Data Science Lead is relevant to routing evaluation; budget sponsorship remains unknown.','Reproducible paratransit schedule tests following a delayed pickup; track knock-on passenger delays and schedule changes.'),
'weavegrid':('Technical Lead Manager is nearer charging implementation than president; exact DISCO ownership unconfirmed.','Test earlier driver departure requests under local grid constraints; regression cases distinguish impossible requests from recoverable schedules.'),
'inorbit':('Lead Architect is current verified company employee; do not use former CTO match now at Ekumen.','Simulated paused-robot tasks for orchestration regression testing, exposing wait/reassign queue effects without assuming a current failure.')}

plans=[]
for old in original['emails']:
 c,a,oldpid=old['contact_id'].split('/');base=Path('campaigns')/c/'accounts'/a
 shutil.copytree(base,review/'source-before'/c/a,ignore=shutil.ignore_patterns('technical-owner-discovery-2026-09-16.json'))
 brief=json.load(open(base/'research.json'));reason,angle=angles[a];prior=next(p for p in brief['stakeholders'] if p['id']==oldpid)
 if a in chosen:
  r=chosen[a];p=r['person'];pid=slug(p['name']);role=p['title'];fid=a+'-technical-owner-20260916'
  owner={'id':pid,'name':p['name'],'role':role,'rank':1,'seniority':'technical_owner','department':'engineering' if 'Product' not in role else 'product','reason':reason+' Budget and signing authority unconfirmed.','fact_ids':[fid],'apollo_id':p['id']}
  brief['facts'].append({'id':fid,'entity_id':pid,'text':p['name']+' is reported by Apollo as '+role+' at '+brief['company']['name']+'.','evidence':[{'source_id':r['source_id'],'quote':role}]})
  prior['rank']=2;prior['reason']='Prior unsent target retained for history; superseded by '+p['name']+'. Do not contact in parallel.'
  brief['stakeholders']=[owner,prior]
  contact=normalize_contact(p,owner,r['domain'],r['source_id'],r['observed_at'])
  location=', '.join(p[k] for k in ('city','state','country') if p.get(k));sid=r['source_id'];tzsource='apollo_person_location'
  if a in ('rideco','open-ocean-robotics'):
   url='https://www4.lead411.com/Alexander_Bailey_53964343.html' if a=='rideco' else 'https://ca.linkedin.com/in/ari-robinson'
   src=next(s for s in web if s['url']==url);sid=src['id'];tzsource='public_person_location';location='Kitchener, Ontario, Canada' if a=='rideco' else 'Victoria, British Columbia, Canada'
  schedule={'timezone':zones[a],'timezone_source':tzsource,'source_id':sid,'location':location,'assumed_office_location':False,'mapping_note':'Mapped from captured person location. Country-only mappings used only where current civil time is uniform; not inferred from company headquarters.'}
  if a=='rideco':schedule['mapping_note']='Person-specific Lead411 location corroborates Ontario; current role sourced separately from RideCo and Apollo.'
  write_json(base/pid/'contact.json',contact)
 else:
  pid=oldpid;owner=prior;owner['reason']=reason+' Budget and signing authority unconfirmed.'
  contact=json.load(open(base/pid/'contact.json'));schedule=json.load(open(base/pid/'schedule.json'))
 # Add the material fact discovered during current research.
 if a=='earthmover':
  src=next(s for s in web if s['url']=='https://hr.linkedin.com/in/mrbriandavis')
  brief['facts'].append({'id':'earthmover-existing-fault-injection','entity_id':a,'text':'Earthmover describes fault injection against real network failures in its Icechunk 2 release announcement, reposted by Brian Davis.','evidence':[{'source_id':src['id'],'quote':'fault injection tested against real network failures'}]})
 brief['hypotheses']=[{'statement':angle,'confidence':'medium','basis':[a+'-work',a+'-sender-proof']}]
 brief['recommended_motion'].update(stage='technical_contract',ask='Ask whether this concrete engineering task is on their backlog; explicitly offer Andrew for a small paid contract outside his co-op. A 15-minute conversation is optional after a yes.')
 brief['message_strategy'].update(central_reason=angle,problem_altitude='Relevant technical or product owner; handover of working code and tests, with the need explicitly conditional.',expose_facts=[a+'-work']+(['earthmover-existing-fault-injection'] if a=='earthmover' else []),why_now=None,why_now_basis=[])
 brief['message_strategy']['do_not_claim']=['This team has the hypothesized gap or lacks tests','Contract budget, procurement speed, signing authority or a response probability','Guaranteed savings or system safety','Full-time availability, agreed dates, price, or data access','Prior relationship or a resume attachment']
 brief['qualification']['basis']=[a+'-work',a+'-sender-proof']+owner['fact_ids']
 validate_brief(brief,read_sources(Path('campaigns')/c));write_json(base/'research.json',brief);write_json(base/'contacts.json',brief['stakeholders'])
 (base/'strategy.md').write_text('# '+brief['company']['name']+'\n\n## September 16 revision\n\n'+reason+'\n\nProposed work, conditional on actual need: '+angle+'\n\nAsk: '+brief['recommended_motion']['ask']+'\n\nNo observed buying intent, budget, agreed scope or response evidence.\n')
 packet={'phase':'research_and_strategy_complete_before_writing','completed_at':at,'company':brief['company'],'recipient':owner,'facts':brief['facts'],'hypotheses':brief['hypotheses'],'strategy':brief['message_strategy'],'sender':'Andrew personally, UofT student on co-op in London, UK; small paid contract outside co-op','style_authority':'Current user supplied Earthmover/Realtime examples supersede earlier fixed RL/MCTS intro and habitual curiosity language.','unknowns':['Actual backlog priority','External contractor budget','Decision maker and payment timeline','Permitted inputs and hours required'],'history':'Existing company-wide Gmail searches are retained with original observed_at; no fabricated fresh retrieval. Exact sender mailbox must be checked before sending.'}
 write_json(base/'technical-owner-strategy-2026-09-16.json',packet)
 plans.append({'old':old,'campaign':c,'account':a,'person_id':pid,'contact_id':'/'.join([c,a,pid]),'contact':contact,'owner':owner,'schedule':schedule,'angle':angle,'reason':reason,'research_version':hashlib.sha256((base/'research.json').read_bytes()).hexdigest()})
write_json(root/'plans.json',plans);write_json(review/'recipient-plan.json',plans)
(review/'current-direction.md').write_text('''# Current direction: September 16\n\nAndrew is selling his own contract engineering work. Rewrite today\'s 30, retaining original drafts and state in this folder. Prefer a relevant hands-on owner with a route to budget. Technical founders remain appropriate where actual ownership supports that choice. Do not equate seniority with purchasing authority.\n\nCopy: short current introduction, relevant built work, one concrete product surface, a conditional task, working code/tests handed over, explicit small paid contract, and one answerable backlog question. No fixed duration or price in first touch. No invented pain, fake urgency, quantified payoff or response prediction. Current user examples override older fixed biography, tentative wording, and generic spam-token bans on ordinary words and greetings.\n\n25 of 30 recipients replaced. Five technical founders/CTOs retained for actual technical relevance. Each provider address is verified; delivery is not guaranteed. Role and scope ambiguities remain recorded. Nothing sent or scheduled in Gmail.\n''')
print(json.dumps({'plans':len(plans),'retargeted':sum(p['contact_id']!=p['old']['contact_id'] for p in plans),'backup':str(review)},indent=2))
