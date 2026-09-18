"""Hiring and operational pressure as evidence, not applications or automatic openers."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen,Request
import argparse,hashlib,json,subprocess,xml.etree.ElementTree as ET
from research import WORKSPACE,campaign,read_sources,add_source,write_json,slug
from state import connect,stamp,instant


def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS signals(id TEXT PRIMARY KEY,campaign TEXT,account_id TEXT,type TEXT,source_id TEXT,event_at TEXT,observed_at TEXT,active INTEGER,payload TEXT);
      CREATE TABLE IF NOT EXISTS job_versions(id TEXT,version TEXT,observed_at TEXT,payload TEXT,PRIMARY KEY(id,version));
      CREATE TABLE IF NOT EXISTS watches(id TEXT PRIMARY KEY,campaign TEXT,account_id TEXT,kind TEXT,target TEXT,identity_source TEXT,last_checked_at TEXT,last_error TEXT);''')


def add_pressure(db,path,account,value):
    schema(db);sources=read_sources(path)
    if value.get('type') not in {'regulation','funding','expansion','incident','hiring','target','news'}:raise ValueError('Unknown signal type')
    e=value.get('evidence',{});source=sources.get(e.get('source_id'))
    if not source or not e.get('quote') or e['quote'] not in source['text']:raise ValueError('Pressure signal needs an actual captured source quote')
    if not value.get('observed_fact') or not value.get('owner') or not value.get('inference'):raise ValueError('Separate observed fact, its owner and the hypothesis')
    if value.get('type')=='regulation':
        if not value.get('jurisdiction') or not value.get('legal_obligation_owner'):raise ValueError('Resolve jurisdiction and who owns the legal obligation')
        if value.get('should_mention_in_email') and not value.get('applicability_evidence'):raise ValueError('Do not assign producer obligations to a processor without evidence')
        for ref in value.get('applicability_evidence',[]):
            s=sources.get(ref.get('source_id'))
            if not s or not ref.get('quote') or ref['quote'] not in s['text']:raise ValueError('Regulatory applicability needs evidence')
    event_at=value.get('event_at')
    if event_at:instant(event_at)
    value.setdefault('should_mention_in_email',False)
    value.setdefault('budget_interpretation','Unknown discretionary budget; funding/headcount does not prove external project budget')
    sid=value.get('id') or hashlib.sha256((str(path)+account+e['source_id']+value['observed_fact']).encode()).hexdigest()[:22]
    with db:db.execute('INSERT INTO signals VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,observed_at=excluded.observed_at,active=excluded.active',
        (sid,path.name,account,value['type'],e['source_id'],event_at,source['observed_at'],1,json.dumps(value)))
    return sid


def watch(db,path,account,kind,target,identity_source):
    schema(db)
    if kind not in {'ats','rss','page'}:raise ValueError('Watch ATS feeds, RSS/Atom or a company/regulator page')
    source=read_sources(path).get(identity_source)
    if not source or target not in source['text']+source['url']:raise ValueError('Tie the watch target to the researched company using a captured careers/source link')
    wid=hashlib.sha256((path.name+account+kind+target).encode()).hexdigest()[:20]
    with db:db.execute('INSERT OR IGNORE INTO watches(id,campaign,account_id,kind,target,identity_source) VALUES(?,?,?,?,?,?)',(wid,path.name,account,kind,target,identity_source))
    return wid


def ingest_jobs(db,path,account,capture,identity_source):
    schema(db)
    if identity_source not in read_sources(path):raise ValueError('Resolve the board-company identity before ingestion')
    result=capture.get('result',{})
    if result.get('error') or 'jobs' not in result:raise ValueError('ATS unavailable is not evidence of no hiring: '+str(result.get('error','no result')))
    at=capture['observed_at'];source_ids=[]
    for i,row in enumerate(capture.get('capture',[])):
        sid='ats-'+hashlib.sha256((row['url']+row['text']+at).encode()).hexdigest()[:20]
        add_source(path,{'id':sid,'url':row['url'],'text':row['text'],'observed_at':row['observed_at'],'tool':'ats-jobs public API','tool_ref':sid});source_ids.append(sid)
    if not source_ids:raise ValueError('ATS result must retain raw provider evidence')
    counts={'new':0,'changed':0,'unchanged':0,'closed':0};current=[]
    with db:
        for job in result['jobs']:
            if not job.get('id') or not job.get('url'):continue
            jid='job-'+hashlib.sha256((path.name+account+result['provider']+str(job['id'])).encode()).hexdigest()[:22];current.append(jid)
            version=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
            prev=db.execute('SELECT payload FROM signals WHERE id=?',(jid,)).fetchone()
            same=db.execute('SELECT 1 FROM job_versions WHERE id=? AND version=?',(jid,version)).fetchone()
            counts['unchanged' if same else 'changed' if prev else 'new']+=1
            db.execute('INSERT OR IGNORE INTO job_versions VALUES(?,?,?,?)',(jid,version,at,json.dumps(job)))
            payload={'job':job,'version':version,'provider':result['provider'],'source_ids':source_ids,'identity_source':identity_source,'classification':None,'expansion_vs_replacement':'unknown','external_contract_budget':'unknown','should_mention_in_email':False,'description_complete':bool(job.get('description'))}
            if same and prev:payload['classification']=json.loads(prev['payload']).get('classification')
            db.execute('INSERT INTO signals VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET observed_at=excluded.observed_at,active=1,payload=excluded.payload',
                (jid,path.name,account,'hiring',source_ids[0],job.get('publishedAt'),at,1,json.dumps(payload)))
        # A capped/partial feed must not mark missing roles closed.
        if len(result['jobs'])<200:
            for row in db.execute("SELECT id FROM signals WHERE campaign=? AND account_id=? AND type='hiring' AND active=1",(path.name,account)).fetchall():
                if row['id'] not in current:db.execute('UPDATE signals SET active=0 WHERE id=?',(row['id'],));counts['closed']+=1
    return counts


def classify_job(db,sid,value):
    schema(db);row=db.execute("SELECT * FROM signals WHERE id=? AND type='hiring'",(sid,)).fetchone()
    if not row:raise ValueError('Unknown captured job')
    payload=json.loads(row['payload']);text=payload['job'].get('description','')
    if not text:raise ValueError('Read the full JD before classifying the problem')
    if not value.get('evidence_quotes') or any(q not in text for q in value['evidence_quotes']):raise ValueError('Job interpretation must cite actual description text')
    if not value.get('technical_priorities') or not value.get('likely_owner'):raise ValueError('Resolve the problem and likely technical owner, not just a keyword count')
    for k in ('technical_overlap','mission_interest','active_problem','bounded_project','ability_to_pay'):
        if type(value.get(k)) not in (float,int) or not 0<=value[k]<=1:raise ValueError('Signal relevance components use 0–1 judgments')
    if value.get('external_contract_budget','unknown')!='unknown':
        sources=read_sources(campaign(row['campaign']))
        refs=value.get('budget_evidence',[])
        if not refs or any(e.get('source_id') not in sources or not e.get('quote') or e['quote'] not in sources[e['source_id']]['text'] for e in refs):
            raise ValueError('A vacancy alone does not prove contract budget; retain separate captured budget evidence')
    age=None
    if row['event_at']:
        try:age=max(0,(datetime.now(timezone.utc)-instant(row['event_at'])).days)
        except ValueError:pass
    freshness=2**(-age/30) if age is not None else .35
    score=freshness
    for k in ('technical_overlap','mission_interest','active_problem','bounded_project','ability_to_pay'):score*=value[k]
    payload['classification']={**value,'freshness':freshness,'priority_signal':round(score,4),'interpretation':'Ranking signal, not probability or a job application'}
    with db:db.execute('UPDATE signals SET payload=? WHERE id=?',(json.dumps(payload),sid))
    return payload['classification']


def poll(db):
    schema(db);reports=[]
    for w in db.execute('SELECT * FROM watches').fetchall():
        path=campaign(w['campaign'])
        try:
            if w['kind']=='ats':
                proc=subprocess.run(['node',str(Path(__file__).with_name('fetch-jobs.mjs')),w['target']],capture_output=True,text=True,timeout=150)
                if proc.returncode:raise ValueError('ATS fetch failed')
                result=ingest_jobs(db,path,w['account_id'],json.loads(proc.stdout),w['identity_source'])
            else:
                # Feed/page capture only. Codex resolves event owner, relevance and claims separately.
                with urlopen(Request(w['target'],headers={'User-Agent':'AndrewOutreachResearch/1.0'}),timeout=25) as r:raw=r.read(5_000_000).decode('utf-8','replace')
                sid='watch-'+hashlib.sha256((w['target']+raw).encode()).hexdigest()[:22]
                if sid not in read_sources(path):add_source(path,{'id':sid,'url':w['target'],'text':raw,'observed_at':stamp(),'tool':'Public source watcher','tool_ref':sid})
                result={'source_id':sid,'needs_agent_triage':True}
            with db:db.execute('UPDATE watches SET last_checked_at=?,last_error=NULL WHERE id=?',(stamp(),w['id']))
            reports.append({'watch':w['id'],'result':result})
        except (ValueError,OSError,subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
            with db:db.execute('UPDATE watches SET last_checked_at=?,last_error=? WHERE id=?',(stamp(),type(exc).__name__,w['id']))
            reports.append({'watch':w['id'],'error':str(exc)[:200]})
    return reports


def projection(db):
    schema(db);rows=[]
    for r in db.execute('SELECT * FROM signals ORDER BY observed_at DESC'):
        v=dict(r);v['payload']=json.loads(v['payload']);rows.append(v)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('poll');s.add_parser('list')
    w=s.add_parser('watch');w.add_argument('campaign');w.add_argument('account');w.add_argument('kind');w.add_argument('target');w.add_argument('source')
    a=s.add_parser('pressure');a.add_argument('campaign');a.add_argument('account');a.add_argument('json')
    a=s.add_parser('classify-job');a.add_argument('id');a.add_argument('json')
    a=p.parse_args()
    with connect() as db:
        if a.cmd=='poll':result=poll(db)
        elif a.cmd=='list':result=projection(db)
        elif a.cmd=='watch':result=watch(db,campaign(a.campaign),a.account,a.kind,a.target,a.source)
        elif a.cmd=='pressure':result=add_pressure(db,campaign(a.campaign),a.account,json.loads(Path(a.json).read_text()))
        else:result=classify_job(db,a.id,json.loads(Path(a.json).read_text()))
    print(json.dumps(result,ensure_ascii=False,indent=2))
