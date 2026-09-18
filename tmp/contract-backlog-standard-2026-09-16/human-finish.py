import json,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
import operations
from state import get,eligible,event
from research import write_json
from readiness import blockers
from campaign_lint import rows_for,lint,check,save_review
from mission import review_campaign
root=Path('tmp/contract-backlog-standard-2026-09-16');review=Path('campaigns/contract-2026-09-16/reviews/human-progression-2026-09-16');rows=json.load(open(root/'human-finalized.json'));now=datetime.now(timezone.utc);at=now.isoformat()
with operations.connect() as db:
 for r in rows:
  q=db.execute('select id,body,subject,status from scheduled_sends where contact_id=?',(r['contact_id'],)).fetchone();assert q and q['body']==r['body'] and q['subject']==r['subject'];r['action_id']=q['id']
 reports={}
 for campaign in {r['campaign'] for r in rows}:
  report=check(db,campaign);saved=json.load(open(review/(campaign+'-semantic-review.json')));saved['fingerprint']=report['fingerprint'];reports[campaign]=save_review(db,campaign,saved);write_json(review/(campaign+'-semantic-review.json'),saved)
 db.commit();write_json(review/'campaign-lint.json',reports)
 selected={r['contact_id'] for r in rows}
 # Verify source files reconstruct the exact same current draft and checks.
 for campaign in {r['campaign'] for r in rows}:
  catalog=review_campaign(Path('campaigns')/campaign)
  for account in catalog['accounts']:
   for p in account['contacts']:
    cid='/'.join([campaign,account['id'],p['id']])
    if cid not in selected:continue
    r=next(r for r in rows if r['contact_id']==cid);assert p['body']==r['body'] and p['subject']==r['subject']
    if not r['held']:assert not p['blockers'],(cid,p['blockers'])
    else:assert p['draft_status']=='held' and p['blockers']
 # Refresh existing daily exports from durable state, retaining conditional followups.
 exportdir=Path('campaigns/contract-week-2026-09-16');backup=review/'previous-exports';backup.mkdir(exist_ok=True)
 for day in ('2026-09-16','2026-09-17','2026-09-18'):
  jp=exportdir/('emails-'+day+'.json');mp=jp.with_suffix('.md');prior=json.load(open(jp))
  shutil.copy2(jp,backup/jp.name);shutil.copy2(mp,backup/mp.name)
  export=[x for x in prior if x.get('type')!='initial']
  for q in db.execute("select s.*,c.name,c.email,c.recipient_timezone,c.context from scheduled_sends s join contacts c on c.id=s.contact_id where s.queue_date=? and c.engine='technical_contract' and s.touch_number=1 and s.status in ('review','approved','held','gmail_scheduled','cancel_required') order by s.send_at",(day,)):
   x=dict(q);ctx=json.loads(x.pop('context'));x.update(company=ctx.get('company_name'),company_key=ctx.get('parent_company_key'),recipient=x.pop('email'),role=ctx.get('role'),date=day,type='initial',draft_hash=ctx.get('factual_review_hash'),attachments=ctx.get('attachments',[]),send_authorized=False);export.append(x)
  write_json(jp,export)
  text=['# Contract Work — '+day,'Current local queue export. No send or Gmail schedule authorization. Held entries are not ready to send. Conditional follow-ups retain their original history and refresh requirements.']
  for x in export:text.append('## '+str(x.get('company',''))+' — '+str(x.get('name',''))+'\n\nStatus: '+str(x.get('status'))+'\n\nTo: '+str(x.get('recipient',x.get('email','')))+'\n\nSubject: '+str(x.get('subject',''))+'\n\n'+str(x.get('body','')))
  mp.write_text('\n\n'.join(text)+'\n')
write_json(root/'human-applied.json',rows);write_json(review/'applied.json',rows)

def export_rows(subset):
 return [{'number':i,'contact_id':r['contact_id'],'action_id':r['action_id'],'company':r['brief']['company']['name'],'recipient_name':r['owner']['name'],'recipient_role':r['owner']['role'],'to':r['contact']['email'],'from':r['old']['sender_mailbox'],'subject':r['subject'],'body':r['body'],'status':'held' if r['held'] else 'review','recommended_send_utc':r['schedule']['recommended_send_utc'],'recommended_send_local':r['schedule']['recommended_send_local'],'draft_hash':r['draft_hash'],'change_reason':r['reason']} for i,r in enumerate(subset,1)]
def markdown(title,subset):
 parts=['# '+title,'Latest human-progression revision. Local drafts only; nothing sent or scheduled in Gmail. The supplied Archy/Nic bodies are preserved exactly. Diligent remains held for unresolved current Moxi responsibility.']
 for r in export_rows(subset):parts.append('## '+str(r['number'])+'. '+r['company']+' — '+r['recipient_name']+'\n\n**Status:** '+r['status']+'  \n**To:** '+r['to']+'  \n**Role:** '+r['recipient_role']+'  \n**Local recommendation:** '+r['recommended_send_local']+'  \n**Subject:** '+r['subject']+'\n\n'+r['body'])
 return '\n\n'.join(parts)+'\n'
todayrows=sorted([r for r in rows if r['is_today']],key=lambda r:r['schedule']['recommended_send_utc']);listed=[r for r in rows if r['is_listed']]
batch={'date':'2026-09-16','positioning':'Andrew as an individual contract worker; human technical interest, genuine motivation and a small contract ask','sending_enabled':False,'count':30,'retargeted':25,'revision':'human-progression-2026-09-16','emails':export_rows(todayrows)}
write_json(Path('campaigns/contract-2026-09-16/reviews/september-16-selected-30/batch.json'),batch);write_json(review/'today-30.json',batch);write_json(review/'listed-30.json',{'count':30,'held':1,'emails':export_rows(listed)})
Path('campaigns/contract-2026-09-16/30-emails-for-september-16.md').write_text(markdown('30 Contract Work emails — September 16, 2026',todayrows))
(review/'listed-30-emails.md').write_text(markdown('The 30 reviewed companies — revised voice',listed));(review/'all-55-emails.md').write_text(markdown('All 55 revised Contract Work drafts',rows))
direction='# Current Contract Work direction — September 16\n\nLatest correction: Neil/FIDO plus Andrew\'s supplied Archy/Nic bodies are the preferred seeds. Preserve specific technical interest, actual skill connection and genuine motivation, then a small contract ask, tentative idea, deference and natural call. No mandatory paid/backlog/15-minute wording or resume-bullet intro. Do not manufacture impact or force a template.\n\n55 drafts revised, including today\'s 30 and the overlapping named 30. Three new technical contacts; existing Mariano reused for SimScale; duplicate Chloris approach removed. Diligent is held for unresolved current Moxi responsibility. Prior source versions and queue snapshot are preserved here. No Gmail send/schedule action.\n'
(review/'current-direction.md').write_text(direction);Path('campaigns/contract-2026-09-16/current-direction-2026-09-16.md').write_text(direction)
print(json.dumps({'rewritten':55,'today':30,'listed':30,'held':1,'new_contacts':3,'reused_existing_contact':'Mariano Barrios / SimScale','source_queue_consistent':True,'campaign_reviews_current':all(r['review_current'] for r in reports.values()),'sent':0,'gmail_scheduled':0},indent=2))
