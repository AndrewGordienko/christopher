"""Collection diagnostics and a fingerprint-bound critic gate. Never sends mail."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

SEMANTIC_CHECKS = ('thought_continuity', 'distinct_problem_reasoning', 'grounded_facts', 'appropriate_subjects')


def rows_for(db, campaign):
    rows = []
    for r in db.execute('''SELECT s.*,c.campaign,c.account_id,c.entity_key,c.rank,
            c.recipient_timezone,c.context,c.research_version FROM scheduled_sends s
            JOIN contacts c ON c.id=s.contact_id WHERE c.campaign=? AND s.body IS NOT NULL
            AND s.status IN ('held','review','approved','gmail_scheduled','cancel_required','sent')
            ORDER BY s.id''', (campaign,)):
        d = dict(r); ctx = json.loads(d.pop('context'))
        d.update(recipient=ctx.get('email'), company_key=ctx.get('parent_company_key') or d['entity_key'],
                 timezone_source=ctx.get('timezone_source') or ctx.get('timezone_evidence'),
                 attachments=ctx.get('attachments', []),
                 minimum_spacing_seconds=ctx.get('schedule_policy', {}).get('minimum_spacing_seconds', 600))
        rows.append(d)
    return rows


def batch_fingerprint(rows):
    keys = ('id','contact_id','recipient','company_key','subject','body','send_at',
            'sender_mailbox','recipient_timezone','timezone_source','research_version','attachments','minimum_spacing_seconds')
    data = [{k:r.get(k) for k in keys} for r in rows]
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def personalized(body):
    # Exclude genuine biography/sign-off, not repeated company reasoning or asks.
    paragraphs = re.split(r'\n\s*\n', body)
    return [p.strip() for p in paragraphs if p.strip() and
            not re.match(r"^(Hi |Hello |Best,|Andrew$|I['’]m a UofT student|We['’]re a .*UofT)", p.strip())]


def lint(rows):
    issues = []
    def add(code, label, ids, severity='warning'):
        issues.append(dict(code=code,label=label,action_ids=sorted(set(ids)),severity=severity))
    active = [r for r in rows if r['status'] != 'sent']
    n = len(active); threshold = max(4, (n+2)//3)
    text = {r['id']:'\n\n'.join(personalized(r['body'])).replace('’',"'").lower() for r in active}
    patterns = {
        'fit_scaffold': r'seemed (?:like a |particularly )?(?:good fit|interesting)|felt like a .*good fit',
        'looking_scaffold': r"i've been looking for ways to use that skillset",
        'one_thought': r'one thought was',
        'wondering_ask': r'i was wondering if there might be',
        'generic_redirection': r"but i'd much rather work on whatever problem",
        'harness': r'(?:simulation and )?evaluation harness',
        'fake_impact': r'put my skills to good use|make a positive impact|make the world better|mission-driven work',
    }
    for code, pattern in patterns.items():
        ids = [i for i,t in text.items() if re.search(pattern,t)]
        if len(ids) >= threshold: add(code, f'{len(ids)} emails repeat “{code.replace("_"," ")}” wording; compare the actual thoughts', ids)
    endings = defaultdict(list)
    for r in active:
        ps=personalized(r['body'])
        if ps: endings[ps[-1]].append(r['id'])
    repeated = [ids for p,ids in endings.items() if len(ids)>=threshold and len(p.split())>8]
    if repeated: add('identical_ending','The same closing paragraph recurs; retain only where it is the natural next step',[i for ids in repeated for i in ids])
    project_ids=[r['id'] for r in active if re.search(r'\bproject$',r['subject'],re.I)]
    if n>=5 and len(project_ids)/n>=.7: add('subject_grammar','Most subjects end in “project”; inspect whether they are independently plausible',project_ids)
    groups=defaultdict(list)
    for r in active:
        if r.get('send_at') and r['status'] != 'held': groups[(r['sender_mailbox'],r['company_key'])].append(r['id'])
        if not r.get('recipient_timezone'): add('timezone','Recipient timezone is unresolved',[r['id']],'error')
    for ids in groups.values():
        if len(ids)>1: add('account_collision','More than one queued recipient/touch at an account',ids,'error')
    times=defaultdict(list)
    for r in active:
        if not r.get('send_at') or r['status']=='held': continue
        dt=datetime.fromisoformat(r['send_at'].replace('Z','+00:00'))
        if dt.tzinfo is None: add('timezone','Scheduled time lacks an offset',[r['id']],'error');continue
        times[r['sender_mailbox']].append((dt.astimezone(timezone.utc),r))
        try:
            local=dt.astimezone(ZoneInfo(r['recipient_timezone']))
            if local.weekday()>4 or not 8<=local.hour<18: add('work_window','Time falls outside ordinary recipient-local working hours',[r['id']])
        except (KeyError,ValueError,TypeError): add('timezone','Recipient IANA timezone is invalid',[r['id']],'error')
    for sends in times.values():
        sends.sort(key=lambda x:x[0])
        minutes=[(t,r) for t,r in sends if t.minute%5==0]
        if len(sends)>=5 and len(minutes)/len(sends)>=.8: add('round_batch','Most batch timestamps fall on five-minute marks',[r['id'] for t,r in minutes])
        for (a,ra),(b,rb) in zip(sends,sends[1:]):
            minimum=max(60,ra.get('minimum_spacing_seconds',600),rb.get('minimum_spacing_seconds',600))
            if (b-a).total_seconds()<minimum: add('burst','Mailbox sends violate the configured minimum spacing',[ra['id'],rb['id']],'error')
        for i in range(len(sends)-3):
            part=sends[i:i+4];gaps=[int((b[0]-a[0]).total_seconds()) for a,b in zip(part,part[1:])]
            if len(set(gaps))==1 and gaps[0]<=3600: add('regular_spacing','Four consecutive sends use exactly the same interval',[r['id'] for t,r in part])
    # Coalesce identical warning codes while preserving actual affected records.
    merged={}
    for issue in issues:
        if issue['code'] in merged: merged[issue['code']]['action_ids']=sorted(set(merged[issue['code']]['action_ids']+issue['action_ids']))
        else: merged[issue['code']]=issue
    return {'fingerprint':batch_fingerprint(rows),'count':n,'issues':list(merged.values())}


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS campaign_reviews(campaign TEXT PRIMARY KEY,
        fingerprint TEXT NOT NULL, reviewed_at TEXT NOT NULL, review TEXT NOT NULL)''')


def check(db,campaign):
    schema(db); report=lint(rows_for(db,campaign))
    saved=db.execute('SELECT * FROM campaign_reviews WHERE campaign=?',(campaign,)).fetchone()
    review=json.loads(saved['review']) if saved and saved['fingerprint']==report['fingerprint'] else None
    unresolved=[x for x in report['issues'] if x['severity']=='error' or not review or not review.get('resolutions',{}).get(x['code'])]
    report.update(campaign=campaign,review_current=review is not None,
                  eligible_for_approval=not unresolved and (report['count']<3 or review is not None),
                  unresolved=unresolved)
    return report


def save_review(db,campaign,review):
    report=check(db,campaign)
    if review.get('fingerprint')!=report['fingerprint']: raise ValueError('Batch changed; rerun the critic')
    if any(x['severity']=='error' for x in report['issues']): raise ValueError('Fix scheduling/account errors before review')
    if not review.get('reason') or not all(review.get('semantic_checks',{}).get(k) is True for k in SEMANTIC_CHECKS):
        raise ValueError('Separate semantic review and explanation required')
    if any(not review.get('resolutions',{}).get(x['code']) for x in report['issues']): raise ValueError('Resolve each actual lint flag')
    db.execute('INSERT OR REPLACE INTO campaign_reviews VALUES(?,?,?,?)',
               (campaign,report['fingerprint'],datetime.now(timezone.utc).isoformat(),json.dumps(review)))
    return check(db,campaign)


def require_ready(db,campaign):
    report=check(db,campaign)
    if not report['eligible_for_approval']:
        raise ValueError('Campaign review required: '+('; '.join(x['label'] for x in report['unresolved']) or 'compare the current batch before approval'))


if __name__=='__main__':
    from state import connect
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['check','review']);parser.add_argument('campaign');parser.add_argument('review',nargs='?',type=Path)
    args=parser.parse_args()
    with connect() as db:
        result=save_review(db,args.campaign,json.loads(args.review.read_text())) if args.command=='review' else check(db,args.campaign)
    print(json.dumps(result,ensure_ascii=False,indent=2))
