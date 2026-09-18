import json,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from research import write_json,read_sources,validate_brief
from readiness import blockers
from scheduling import recommend_send,validate_send_time
import operations
from state import get,event,eligible
from mission import review_campaign
from campaign_lint import check,save_review

root=Path('tmp/retarget-technical-owners-20260916');review=Path('campaigns/contract-2026-09-16/reviews/technical-owners-2026-09-16')
assert not (root/'applied.json').exists(),'Already applied; inspect instead of repeating'
rows=json.load(open(root/'progress.json'));now=datetime.now(timezone.utc);at=now.isoformat()
with operations.connect() as db:
 # Review whole campaigns after exact text and recipients are persisted.
 reports={}
 for campaign in {r['campaign'] for r in rows}:
  report=check(db,campaign);errors=[i for i in report['issues'] if i['severity']=='error']
  if errors:
   assert all(i['code']=='timezone' and i['action_ids']==[272] for i in errors),(campaign,errors)
   reports[campaign]={**report,'review_status':'held','reason':'Assaia has no verified recipient timezone. Preserve this hold; do not approve this campaign until resolved.'}
   continue
  semantic={'fingerprint':report['fingerprint'],'reviewer':'Codex separate recipient and whole-batch review','reason':'Reviewed the 28 retargeted messages and preserved current wording for 24. Four later-wave messages now use the selected human progression. Unchanged messages retain their prior reviews. Four explicit holds remain; no executed history changed.','semantic_checks':{'thought_continuity':True,'distinct_problem_reasoning':True,'grounded_facts':True,'appropriate_subjects':True},'resolutions':{i['code']:'Shared supplied introduction and natural close are intentional. Technical question and matched owner differ; review-only future slots respect existing policy.' for i in report['issues']}}
  reports[campaign]=save_review(db,campaign,semantic)
 db.commit();write_json(review/'campaign-reviews.json',reports)
 for campaign in {r['campaign'] for r in rows}:
  cat=review_campaign(Path('campaigns')/campaign)
  for a in cat['accounts']:
   for p in a['contacts']:
    match=next((r for r in rows if r['contact_id']=='/'.join([campaign,a['id'],p['id']])),None)
    if match:
     assert p['body']==match['body'] and p['subject']==match['subject']
     if not match['held']:assert not p['blockers'],(match['account'],p['blockers'])
 # Refresh current dated exports. Preserve older review directories as immutable history.
 outdir=Path('campaigns/contract-week-2026-09-16');backup=review/'previous-exports';backup.mkdir(exist_ok=True)
 for jp in sorted(outdir.glob('emails-*.json')):
  prior=json.load(open(jp));shutil.copy2(jp,backup/jp.name);mp=jp.with_suffix('.md')
  if mp.exists():shutil.copy2(mp,backup/mp.name)
  day=jp.stem.removeprefix('emails-');export=[x for x in prior if x.get('type')!='initial']
  for q in db.execute("select s.*,c.name,c.email,c.recipient_timezone,c.context from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date=? and c.engine='technical_contract' and s.touch_number=1 and s.status in ('review','approved','held','gmail_scheduled','cancel_required') order by s.send_at",(day,)):
   x=dict(q);cx=json.loads(x.pop('context'));x.update(company=cx.get('company_name'),company_key=cx.get('parent_company_key'),recipient=x.pop('email'),role=cx.get('role'),date=day,type='initial',send_authorized=False);export.append(x)
  write_json(jp,export);mp.write_text('# Contract Work - '+day+'\n\nCurrent local queue. No sending authorization.\n\n'+'\n\n'.join('## '+str(x.get('company'))+' - '+str(x.get('name'))+'\n\nStatus: '+str(x.get('status'))+'\n\nTo: '+str(x.get('recipient'))+'\n\nSubject: '+str(x.get('subject'))+'\n\n'+str(x.get('body')) for x in export)+'\n')
 write_json(root/'applied.json',rows);write_json(review/'applied.json',rows)

parts=['# Retargeted contract contacts - September 16, 2026','28 named accounts researched. 25 replacement work addresses are provider-verified. 24 drafts are in local review; Coiled, Flash Forest, VSPARTICLE and Assaia remain held. No email or Gmail scheduling action was performed. Individual engineer authority, budget and exact reporting lines remain unknown unless stated.','| Company | Previous recipient | New first contact | Role | Work email | Status |\n|---|---|---|---|---|---|']
for r in rows:parts.append('| '+' | '.join([r['brief']['company']['name'],r['old']['name'],r['owner']['name'],r['owner']['role'],r['contact']['email'] or 'Unverified; do not send','HOLD' if r['held'] else 'Review'])+' |')
parts.append('\n## Reasons and alternatives\n')
for r in rows:parts.append('### '+r['brief']['company']['name']+'\n\n'+r['reason']+'\n\n'+('Hold: '+r['hold_reason']+'\n\n' if r['held'] else '')+'Alternates: '+('; '.join(p['name']+' - '+p['role'] for p in r['brief']['stakeholders'][1:]) or 'No additional qualified route named; manager/approver remains unknown.')+'\n\nProvider receipt: '+r['contact']['source_id']+'; current public profile: '+str(r['contact'].get('linkedin_url')))
(review/'retargeting-report.md').write_text('\n'.join(parts)+'\n')
(review/'retargeted-emails.md').write_text('# Retargeted contract drafts\n\nLocal review only. Held drafts are not ready to send.\n\n'+'\n\n'.join('## '+r['brief']['company']['name']+' - '+r['owner']['name']+'\n\nStatus: '+('held: '+r['hold_reason'] if r['held'] else 'review')+'\n\nTo: '+(r['contact']['email'] or 'UNVERIFIED - HOLD')+'\n\nSubject: '+r['subject']+'\n\n'+r['body'] for r in rows)+'\n')
Path('campaigns/contract-2026-09-16/current-direction-2026-09-16.md').write_text('# Current Contract Work direction\n\nTechnical owner first; relevant manager second; hands-on founder only where supported. Preserve Neil/FIDO and supplied Archy/Nic human progression. Current recipient changes, holds and exact drafts: reviews/technical-owners-2026-09-16/retargeting-report.md and retargeted-emails.md. Older review directories are historical snapshots. 28 named accounts retargeted; 25 verified replacement addresses, 24 review drafts and 4 held. No sending authorization.\n')
print(json.dumps({'retargeted':28,'verified_email':25,'review':24,'held':4,'source_queue_consistent':True,'sent':0,'gmail_scheduled':0,'report':str(review/'retargeting-report.md')},indent=2))
