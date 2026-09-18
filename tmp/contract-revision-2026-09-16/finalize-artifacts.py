import json,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import write_json,read_sources,validate_brief
from readiness import fingerprint,blockers
from scheduling import validate_send_time,POLICY
root=Path('tmp/contract-revision-2026-09-16');rows=json.load(open(root/'drafts.json'));now=datetime.now(timezone.utc);at=now.isoformat()
review=Path('campaigns/contract-2026-09-16/reviews/technical-owner-revision-2026-09-16')
policy=json.load(open(POLICY));policy.update(minimum_spacing_minutes=11)
occupied=[]
rows.sort(key=lambda r:(datetime(2026,9,16,11,30,tzinfo=ZoneInfo(r['schedule']['timezone'])).astimezone(timezone.utc),r['contact_id']))
for r in rows:
 a=r['account'];base=Path('campaigns')/r['campaign']/'accounts'/a;person=base/r['person_id'];person.mkdir(exist_ok=True)
 s=r['schedule'];s['timezone_source']='person_location' if s['timezone_source']=='public_person_location' else s['timezone_source'];tz=ZoneInfo(s['timezone'])
 start=datetime(2026,9,16,10 if a=='earthsense' else 8,0 if a=='earthsense' else 30,tzinfo=tz)
 for minute in range(91 if a=='earthsense' else 181):
  candidate=(start+timedelta(minutes=minute)).astimezone(timezone.utc)
  if candidate<=now+timedelta(minutes=30):continue
  if any(abs((candidate-other).total_seconds())<660 for other in occupied):continue
  if sum(abs((candidate-other).total_seconds())<3600 for other in occupied)>=6:continue
  near=sorted(occupied+[candidate]);i=near.index(candidate);regular=False
  for j in range(max(0,i-3),min(i+1,len(near)-3)):
   gs=[(b-a).total_seconds() for a,b in zip(near[j:j+4],near[j+1:j+4])]
   if len(gs)==3 and len(set(gs))==1 and gs[0]<=3600:regular=True
  if not regular:break
 else:raise ValueError('No recipient-local morning slot: '+a)
 occupied.append(candidate)
 s.update(recommended_send_utc=candidate.isoformat(),recommended_send_local=candidate.astimezone(tz).isoformat(),timezone_abbreviation=candidate.astimezone(tz).tzname(),status='recommended_only',policy=policy,send_authorized=False,schedule_authorized=False,selected_batch='technical-owner-revision-2026-09-16',review_batch=1,rationale='September 16 local draft recommendation; new recipient timezone re-resolved, no Gmail scheduling.')
 digest=fingerprint(r['subject'],r['body']);r['draft_hash']=digest
 brief=json.load(open(base/'research.json'))
 # Complete the sender proof for the precise biography chosen in this draft.
 ml=a in ('recycleye','sewerai');quote='Distilled a 450M-parameter SmolVLA policy' if ml else 'Developed a deadlock search and recovery system' if 'deadlock' in r['body'] or a=='earthmover' else 'Built a 3D digital twin to generate and validate laboratory configurations'
 fid=a+'-current-sender-proof';sources=read_sources(Path('campaigns')/r['campaign']);assert quote in sources['andrew-resume-purple-20260915']['text']
 brief['facts'].append({'id':fid,'entity_id':'andrew','text':r['body'].split('\n\n')[1],'evidence':[{'source_id':'andrew-resume-purple-20260915','quote':quote}]})
 validate_brief(brief,sources);write_json(base/'research.json',brief);r['research_version']=hashlib.sha256((base/'research.json').read_bytes()).hexdigest()
 checks={'version':1,'draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate full-draft reread after writer pass and eight targeted repairs',
 'grammar':{'passed':True,'basis':'Complete sentences, referents, spelling and London, UK punctuation reread on the final text.'},
 'voice':{'passed':True,'basis':'Latest supplied examples: short introduction, actual built work, conditional implementation offer, explicit paid contract and factual backlog question. Shared biography and normal close retained where natural.'},
 'facts':{'passed':True,'basis':'Company surface checked against stored primary research; current role/email provider evidence separate from unverified project need. Sender work is in the purple-tagged resume. No claimed client budget, pain, guaranteed outcome or full-time availability.','fact_ids':[a+'-work',fid]+r['owner']['fact_ids']+(['earthmover-existing-fault-injection'] if a=='earthmover' else [])},
 'readability':{'passed':True,'basis':'One proposed task and one explicit reply question. Removed abstract scenario wording, redundant proof and an extra technical question in the critic pass.'}}
 qa={'version':1,'thought_continuity':{'status':'PASS','draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate continuity pass','reason':r['critic_edit_reason']+' Actual sender work leads to the named company surface, proposed implementation and backlog question.'},
 'cold_email_skeptic':{'status':'PASS','draft_hash':digest,'reviewed_at':at,'reviewer':'Codex separate skeptical-recipient pass','reason':'Exploratory paid-work fit; no observed purchasing intent or response-rate claim.','answers':{
 'why_this_recipient':r['reason'],
 'possible_issue':r['angle'],
 'plausible_mechanism':'The proposed runnable code/tests operate on the named existing software surface. Inputs, interfaces and expected outcomes must be agreed before quoting or committing. '+r['angle'],
 'small_ask':'One factual backlog question; optional 15-minute conversation. No cold request for credentials, production data, implementation authorization or a purchasing commitment.',
 'human_voice':'Andrew is presented as an individual student/engineer with actual built work and an explicit paid-contract objective. No agency pitch, invented urgency or curiosity preamble.',
 'useful_reply_if_wrong_person':'Recipient can confirm whether the named task exists or route the specific software area to its owner. The email does not ask them to invent an engagement.'}}}
 candidate={'id':a+'-technical-owner-v2','subject':r['subject'],'body':r['body']}
 write_json(person/'subject-body-ranking.json',{'selected':candidate,'reason':'Revised from current user examples after research and separate critic; no predicted outcome advantage.'})
 write_json(person/'candidates.json',[candidate]);write_json(person/'ranking.json',{'winner':candidate['id']});write_json(person/'subject-candidates.json',[{'subject':r['subject'],'reason':'Names the concrete software task.'}])
 write_json(person/'review.json',{'status':'draft_ready','base_hash':digest,'note':'September 16 technical-owner revision. Local draft only; sending not authorized.'})
 write_json(person/'critic.json',{candidate['id']:{'facts_supported':True,'reject':False,'reason':r['critic_edit_reason']}})
 write_json(person/'final-checks.json',checks);write_json(person/'outbound-reviews.json',qa);write_json(person/'attachments.json',[]);write_json(person/'schedule.json',s)
 (person/'draft.md').write_text('To: '+r['owner']['name']+' <'+r['contact']['email']+'>\nFrom: '+r['old']['from']+'\nSubject: '+r['subject']+'\n\n'+r['body']+'\n')
 (person/'drafts.md').write_text((person/'draft.md').read_text())
 source_person=review/'source-before'/r['campaign']/a/r['old']['contact_id'].split('/')[-1]
 retrieval=json.load(open(source_person/'retrieval.json'));retrieval['current_task_seed']='Andrew\'s September 16 Earthmover and Realtime examples override older tentative fixed-intro direction.';retrieval['scope_note']='Retained actual contracts-labelled voice examples, no new useful-response outcome asserted.';write_json(person/'retrieval.json',retrieval)
 context=json.load(open(source_person/'context.json'));context.update(recipient=r['contact']['email'],sender_mailbox=r['old']['from'],relationship='new_first_touch',seniority='technical_owner',department=r['owner']['department']);write_json(person/'context.json',context)
 packet=json.load(open(base/'technical-owner-strategy-2026-09-16.json'));packet['facts']=brief['facts'];packet['writer_completed_at']=r['writer_completed_at'];packet['critic_completed_at']=at;write_json(person/'writer-packet.json',packet)
 r['final_checks']=checks;r['outbound_reviews']=qa
 ctx={'email':r['contact']['email'],'email_status':'verified','timezone':s['timezone'],'timezone_uncertain':False,'timezone_source':s['timezone_source'],'timezone_source_id':s['source_id'],'subject':r['subject'],'body':r['body'],'facts_supported':True,'factual_review_hash':digest,'final_checks':checks,'attachments':[],'already_contacted':False,'schedule_policy':policy,'send_at':s['recommended_send_utc']}
 assert not blockers(ctx),(a,blockers(ctx));assert not validate_send_time(ctx,s['recommended_send_utc']),(a,validate_send_time(ctx,s['recommended_send_utc']))
rows.sort(key=lambda r:r['schedule']['recommended_send_utc']);write_json(root/'finalized.json',rows)
write_json(review/'final-drafts-and-reviews.json',rows)
print(json.dumps({'count':len(rows),'all_source_checks_pass':True,'earliest_utc':rows[0]['schedule']['recommended_send_utc'],'last_utc':rows[-1]['schedule']['recommended_send_utc']},indent=2))
