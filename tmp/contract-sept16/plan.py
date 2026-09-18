import sys,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path('skills/andrew-email-style/scripts').resolve()))
from scheduling import recommend_send,validate_send_time,POLICY
rows=json.loads(Path('tmp/contract-sept16/selected.json').read_text()); policy=json.loads(POLICY.read_text());policy['minimum_spacing_minutes']=11
start=datetime(2026,9,16,tzinfo=ZoneInfo('Europe/London'));occupied=[]
rows.sort(key=lambda r:(datetime(2026,9,16,11,30,tzinfo=ZoneInfo(r['recipient_timezone'])).astimezone(timezone.utc),r['id']))
for r in rows:
 ctx=json.loads(r['context']);p=Path('campaigns')/r['campaign']/'accounts'/r['account_id']/r['person_id'];saved=json.loads((p/'schedule.json').read_text())
 resolved={k:saved.get(k) for k in ('timezone','timezone_source','source_id','location','assumed_office_location','mapping_note')}
 tz=ZoneInfo(r['recipient_timezone']);day_start=datetime(2026,9,16,8,30,tzinfo=tz)
 for minute in range(181):
  candidate=(day_start+timedelta(minutes=minute)).astimezone(timezone.utc)
  if any(abs((candidate-other).total_seconds())<660 for other in occupied):continue
  if sum(abs((candidate-other).total_seconds())<3600 for other in occupied)>=6:continue
  near=sorted(occupied+[candidate]);i=near.index(candidate);regular=False
  for j in range(max(0,i-3),min(i+1,len(near)-3)):
   gs=[(b-a).total_seconds() for a,b in zip(near[j:j+4],near[j+1:j+4])]
   if len(gs)==3 and len(set(gs))==1 and gs[0]<=3600:regular=True
  if not regular:break
 else:raise ValueError('No slot for '+r['id'])
 schedule={**resolved,'recommended_send_local':candidate.astimezone(tz).isoformat(),'recommended_send_utc':candidate.isoformat(),'timezone_abbreviation':candidate.astimezone(tz).tzname(),'status':'recommended_only','policy':policy}
 dt=datetime.fromisoformat(schedule['recommended_send_utc'].replace('Z','+00:00'));assert dt.astimezone(ZoneInfo('Europe/London')).date()==start.date(),r['id']
 ctx.update(schedule_policy=policy,send_at=schedule['recommended_send_utc']);assert not validate_send_time(ctx,schedule['recommended_send_utc']), (r['id'], validate_send_time(ctx,schedule['recommended_send_utc']))
 occupied.append(dt);r['new_schedule']={**saved,**schedule,'send_authorized':False,'schedule_authorized':False,'selected_batch':'contract-send-today-2026-09-16','rationale':'Selected for September 16 at Andrew\'s request. Recipient-local weekday morning, spaced within shared daily capacity; recommendation only.'};r['new_context']=ctx
rows.sort(key=lambda r:r['new_schedule']['recommended_send_utc']);Path('tmp/contract-sept16/planned.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([{'company':r['new_context']['company_name'],'local':r['new_schedule']['recommended_send_local'],'London':datetime.fromisoformat(r['new_schedule']['recommended_send_utc'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/London')).isoformat()} for r in rows],indent=2))
