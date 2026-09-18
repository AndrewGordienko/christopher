import json,sys,hashlib,re,shutil
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import write_json,add_source,read_sources,validate_brief,slug
from apollo import normalize_contact
from readiness import fingerprint
root=Path('tmp/retarget-technical-owners-20260916'); review=Path('campaigns/contract-2026-09-16/reviews/technical-owners-2026-09-16')
oldrows=json.load(open(root/'before.json')); enriched=json.load(open(root/'enriched.json'))+json.load(open(root/'enriched-extra.json'))
selected={'axle':'Ben Cserkuti','bearing-ai':'Simon Ramirez-Hinestrosa','spoor':'Arnoud Jonker','coiled':'Gabe Joseph','augmentus':'Roy Koo','realtime-robotics':'Xianchao Long','orchard':'Achyut Paudel','gideon':'Filip Mandic'}
alternates={'bearing-ai':['Juan Torres Lopez'],'toffeex-marco':['Nigel Johnston'],'realtime-robotics':['Miheer Gummuluru'],'orchard':['Jerry Sun'],'gideon':['Petra Abicic']}
reasons={
'axle':'Company-authored introduction identifies Ben as optimizing EVs, batteries and heat pumps. Direct energy-optimization champion; financial approver unknown.',
'agtonomy':'Company team spotlight identifies Matt as implementing autonomous vehicle behavior and local obstacle navigation; his profile explicitly names motion planning. Strong turning/recovery owner match.',
'bonsai-robotics':'Head of Autonomy Software Product & Engineering, corroborated by current agricultural-autonomy work. Relevant technical lead and plausible sponsor.',
'bearing-ai':'ML Tech Lead Manager can assess voyage-model/recovery evaluation and route algorithms work. Juan Torres Lopez is a closer algorithms lead but has no verified email. Budget and reporting lines unknown.',
'spoor':'Software Engineering Team Lead at Spoor, with a current public employer match. Plausible software/tracking route; precise ownership of encounter classification needs confirmation. Scott Behrnes was rejected as primary because his refreshed role is camera systems.',
'glacier':'Software Engineering Manager at Glacier. Relevant route for robot software and pick-selection evaluation; the exact planning owner and approval authority remain unconfirmed.',
'terraclear':'Software Architect at TerraClear, a closer technical route than the chairman. Specific routing-algorithm ownership is a hypothesis; ask through the existing planning idea without asserting his responsibility.',
'timefold':'Solver Engineer and named author of official SolverManager documentation. Direct solver/planning route; a champion rather than a presumed budget holder.',
'coiled':'Open-source engineer whose published Coiled work covers Dask scheduling and distributed computation. No verified work email. Florian Jetter was rejected because current enrichment places him at QuantCo.',
'toffeex-marco':'Senior Optimization Engineer with current ToffeeX affiliation and computational-control research. Direct optimization route; Nigel Johnston is a separate engineering-manager alternative, not a proven reporting line.',
'ev-energy-steve':'Virtual Power Plant Tech Lead identified in ev.energy material, with direct grid/flexibility responsibility. Strong technical owner for charging-model evaluation.',
'flash-forest':'Technical Lead, Mechatronics at Flash Forest is closer to deployed machinery than CEO, but the provider address is extrapolated and route-planning ownership is unresolved. Do not use the guessed address.',
'atmo':'Johan is the technical cofounder leading scientific/engineering work, corroborated by Atmo and his current profile. Explicit hands-on founder exception; different route from the commercial CEO.',
'treefera':'Senior Geospatial Engineer & Science Strategy Lead with current Treefera affiliation. Direct scientific/geospatial route for evidence disagreement evaluation.',
'chloris':'Official company bio identifies Felix as Lead Remote Sensing Scientist. Strong change-detection and uncertainty-evaluation owner match.',
'rugged':'Robotics Software Engineer with controls, communication and real-time systems experience. Closer technical champion than the founder; exact route-planning ownership and manager remain unknown.',
'civ-robotics':'Software and Algorithms Team Lead. Direct functional match for positioning-loss, navigation and recovery evaluation; spending authority still unknown.',
'foxglove':'Tech Lead Manager at Foxglove with autonomous-robot software experience. Plausible robotics-data engineering route; exact search/analysis ownership remains to be confirmed.',
'vsp-aaike':'Technical cofounder Tobias Pfeiffer is a potential scientific/product route, but no verified work email was returned. Public partnership descriptions place parts of active-learning/data evaluation with external research partners; internal ownership needs resolving.',
'assaia':'Software Development Manager for the ML Team, current employer corroborated. Relevant event/ETA-model route. Email is verified; location is only Canada, so recipient timezone remains unresolved.',
'neural-concept':'Current Neural Concept researcher whose own site describes 3D neural representation work. Direct model-evaluation champion; exact surrogate-validation responsibility and budget unknown.',
'augmentus':'Senior robotics software developer, corroborated by his current profile and an interview describing testing new features in the robot cell. Plausible path-repair route; Zhang Yuan has a manager title but no verified email.',
'duality':'Robotics Technical Lead whose own profile explicitly describes digital-twin simulation work at Duality. Strong Falcon scene/evaluation owner match.',
'albert':'Senior Machine Learning Scientist, Applications at Albert Invent. Direct applied-ML/experimental-evaluation route; specific formulation-selection ownership and budget unknown.',
'realtime-robotics':'Principal Robotics Scientist whose own profile explicitly describes motion-planning algorithms. Better first route for multi-robot planning than CEO. Miheer is a separately verified engineering-manager alternative.',
'orchard':'ML/CV Research Engineer whose own site identifies current Orchard work in precision agriculture. Strong repeated-observation/perception-evaluation route; Jerry Sun is the Head of Engineering alternative.',
'gideon':'Engineering Manager, independently listed as such by a current technical conference. Closer engineering sponsor than Chief Robotics Officer; exact trailer-planning ownership needs confirmation. Petra is an alternate robotics software team lead.',
'carbonrobotics':'Software Engineering Manager whose recent public post explicitly recruits C++ robot engineers for his team. Relevant robotics-software owner; precise perception-model ownership still needs routing.'}

def strings(v):
 if isinstance(v,str):yield v
 elif isinstance(v,dict):
  for x in v.values():yield from strings(x)
 elif isinstance(v,list):
  for x in v:yield from strings(x)
web=[]
for name in ['web-evidence.json','web-extra.json']:
 for value in strings(json.load(open(root/name))):
  for chunk in value.split('--------------------------------------------------------------------------------'):
   m=re.search(r'\((https?://[^\s)]+)\)',chunk)
   if m and len(chunk)>80:
    web.append({'id':'owner-web-'+hashlib.sha256(chunk.encode()).hexdigest()[:16],'url':m.group(1),'observed_at':datetime.now(timezone.utc).isoformat(),'tool':'web.run','tool_ref':'retarget-research-20260916','text':chunk.strip()})
for campaign in {r['campaign'] for r in oldrows}:
 for source in web:add_source(Path('campaigns')/campaign,source)
write_json(review/'web-evidence.json',web)
q1='in:anywhere {axle.energy agtonomy.com bonsairobotics.ai bearing.ai spoor.ai endwaste.io terraclear.com timefold.ai coiled.io coiled.com toffeex.com ev.energy flashforest.com atmo.ai}'
q2='in:anywhere {treefera.com chloris.earth rugged-robotics.com civrobotics.com foxglove.dev vsparticle.com assaia.com neuralconcept.com augmentus.tech duality.ai albertinvent.com rtr.ai orchard.ai orchard-robotics.com gideon.ai gideonbros.ai carbonrobotics.com}'
at=datetime.now(timezone.utc).isoformat();plans=[]
for idx,old in enumerate(oldrows):
 a=old['account_id'];c=old['campaign'];base=Path('campaigns')/c/'accounts'/a
 candidates=[e for e in enriched if e['account']==a];e=next((e for e in candidates if e['person'].get('name')==selected.get(a)),candidates[0]);p=e['person'];pid=slug(p['name']);fid=a+'-technical-owner-20260916'
 b=json.load(open(base/'research.json'));owner={'id':pid,'name':p['name'],'role':p['title'],'rank':1,'department':'engineering','seniority':'technical_owner','reason':reasons[a],'apollo_id':p['id'],'fact_ids':[fid]}
 b['facts'].append({'id':fid,'entity_id':pid,'text':p['name']+' is reported by current provider enrichment as '+p['title']+' at '+b['company']['name']+'.','evidence':[{'source_id':e['source_id'],'quote':p['title']}]})
 contact=normalize_contact(p,owner,e['domain'],e['source_id'],e['observed_at'])
 if contact['email_status']!='verified':contact.update(email=None,email_usable=False,provider_email_status=contact['email_status'],email_status='unavailable')
 b['archived_stakeholders']=b.get('archived_stakeholders',[])+b['stakeholders'];b['stakeholders']=[owner]
 for n,name in enumerate(alternates.get(a,[]),2):
  alt=next(e for e in candidates if e['person'].get('name')==name);pp=alt['person'];id2=slug(name);f2=a+'-technical-alternate-'+str(n)+'-20260916'
  o={'id':id2,'name':name,'role':pp['title'],'rank':n,'department':'engineering','seniority':'technical_owner','reason':'Sequential alternative only; not a simultaneous email and no proven reporting line. '+('Work email unavailable.' if not pp.get('email') else 'Budget authority unconfirmed.'),'apollo_id':pp['id'],'fact_ids':[f2]}
  b['facts'].append({'id':f2,'entity_id':id2,'text':name+' is reported as '+pp['title']+'.','evidence':[{'source_id':alt['source_id'],'quote':pp['title']}]});b['stakeholders'].append(o)
  write_json(base/id2/'contact.json',normalize_contact(pp,o,alt['domain'],alt['source_id'],alt['observed_at']))
  write_json(base/id2/'review.json',{'status':'held','note':'Research-only alternate; no parallel first touch.'})
 b['qualification']['basis']=list(dict.fromkeys(b['qualification'].get('basis',[])+[fid]));b['message_strategy']['recipient_reason']=reasons[a]
 validate_brief(b,read_sources(Path('campaigns')/c))
 query=q1 if idx<=12 else q2
 history={'complete':True,'source':'https://mail.google.com/mail/u/0/#search/'+quote(query),'tool_ref':'cua-tab-1964896046-no-exact-matches-20260916','account':'gordienko.adg@gmail.com','observed_at':'2026-09-16T11:21:14.078+00:00','messages':[],'search_query':query,'result':'No exact matches','scope_limit':'Live current sending mailbox, all folders, named domains and listed aliases. Prior other-mailbox observations remain separate; unknown aliases and deleted mail are not covered. Recheck before sending.'}
 tz=p.get('time_zone');tzsource=e['source_id'];location=', '.join(p[k] for k in ['city','state','country'] if p.get(k));sourcetype='apollo_person_location'
 if a=='atmo':
  s=next(s for s in web if 'turn81search0' in s['text']);tz='America/Los_Angeles';tzsource=s['id'];location='San Francisco, California, United States (current Atmo experience on public profile)';sourcetype='person_location'
 held_reason=None
 if a=='coiled':held_reason='No verified work address for Gabe; reject Florian because he is now at QuantCo.'
 if a=='flash-forest':held_reason='Jeffery address is extrapolated; flight-planning ownership also needs confirmation.'
 if a=='vsp-aaike':held_reason='No verified work address; resolve internal versus partner ownership of experiment selection.'
 if a=='assaia':held_reason='Verified email and relevant role; recipient timezone unresolved beyond Canada.'
 plan={'old':old,'campaign':c,'account':a,'brief':b,'owner':owner,'contact':contact,'person_id':pid,'contact_id':'/'.join([c,a,pid]),'reason':reasons[a],'held':bool(held_reason),'hold_reason':held_reason,'history':history,'location':{'timezone':tz,'timezone_source':sourcetype if tz else 'unknown','source_id':tzsource,'location':location,'assumed_office_location':False},'research_completed_at':at}
 plans.append(plan)
 write_json(base/'technical-owner-retargeting-20260916.json',{'researched_at':at,'primary':owner,'routes':b['stakeholders'],'superseded':old['name'],'owner_match':reasons[a],'actual_budget':'UNKNOWN','signatory':'UNKNOWN','reporting_line':'UNKNOWN unless explicitly supported','buying_evidence_grade':'plausible buyer, unconfirmed','history':history,'held_reason':held_reason,'no_parallel_outreach':True,'sending_authorized':False})
write_json(root/'plans.json',plans)
print(json.dumps({'researched':len(plans),'verified_primary_emails':sum(r['contact']['email_status']=='verified' for r in plans),'held':{r['account']:r['hold_reason'] for r in plans if r['held']}}))
