#!/usr/bin/env python3
"""Operational CLI for the durable draft queue. No send operation exists."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json
from pathlib import Path
from research import campaign,read_sources,write_json,slug,WORKSPACE
from state import connect,register,sync_thread,decide,build_queue,projection,review_action,DB


def import_campaigns(db):
    from mission import review_campaign,load
    count=0
    for path in sorted((WORKSPACE/'campaigns').glob('*')):
        if not (path/'mission.json').exists(): continue
        if load(path/'mission.json',{}).get('reference_only'): continue
        data=review_campaign(path)
        for account in data['accounts']:
            folder=path/'accounts'/account['id']; brief=load(folder/'research.json')
            research_version=hashlib.sha256((folder/'research.json').read_bytes()).hexdigest()
            for p in account['contacts']:
                context=load(folder/p['id']/'context.json',{})
                profile=load(folder/p['id']/'linkedin-profile.json',None)
                from signals import projection as signal_projection
                related=[s for s in signal_projection(db) if s['campaign']==path.name and s['account_id']==account['id'] and s['active']]
                hiring=max([s['payload'].get('classification',{}).get('priority_signal',0) for s in related if s['payload'].get('classification')]+[0])
                fit=account.get('fit') or {}
                register(db,data['id'],account['id'],p['id'],data['engine'],(brief['company'].get('domain') or brief['company']['id'])+('/'+account['id'] if brief.get('facility') else ''),
                    {**p['readiness_context'],'linkedin_profile':profile,'name':p['name'],'rank':p['rank'],'email':p['email'],'email_status':p['email_status'],'subject':p['subject'],'body':p['body'],
                     'company_name':account['parent_company'],'draft_hold':p['draft_status']=='held','role':p['role'],'company_type':account.get('industry'),'sender_mode':data['mission'].get('sender_mode'),
                     'parent_company_key':brief['company'].get('pause_group') or brief['company'].get('domain') or brief['company']['id'],
                     'company_domains':brief['company'].get('pause_domains',[]),
                     'benchmark_hypothesis':account.get('benchmark_hypothesis'),
                     'pilot_value_case':account.get('pilot_value_case'),'pilot_state':account.get('pilot_state'),
                     'recipient_function':load(folder/p['id']/'writer-packet.json',{}).get('recipient_function') if data['engine']=='wapahki_facility' else None,
                     'primary_only':data['mission'].get('primary_only',False),
                     'pause_on_any_reply':data['mission'].get('pause_on_any_reply',False),
                     'objective':data['mission'].get('objective'),'sender_mailbox':__import__('execution').mailbox_policy(data['engine']).get('sender_mailbox') or context.get('sender_mailbox'),
                     'timezone':p['schedule'].get('timezone'),'qualified':account['qualification']['verdict']=='yes' and p['draft_status']!='skipped',
                     'research_version':research_version,'priority':{'account_fit':fit.get('score',account['qualification'].get('score',50))/100,'recipient_fit':1-(p['rank']-1)*.15,'current_signal':min(1,.5+hiring),'relationship_value':.5}})
                count+=1
    return {'contacts_imported':count}


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--db',type=Path,default=DB)
    commands=parser.add_subparsers(dest='cmd',required=True)
    commands.add_parser('import'); commands.add_parser('status')
    for cmd in ('sync','decide'):
        p=commands.add_parser(cmd);p.add_argument('contact');p.add_argument('json')
    p=commands.add_parser('queue');p.add_argument('--date',default=(datetime.now(timezone.utc)+timedelta(days=1)).date().isoformat());p.add_argument('--capacity',type=int,default=30)
    p=commands.add_parser('review');p.add_argument('action_id',type=int);p.add_argument('status',choices=['approved','skipped','review','held']);p.add_argument('--approval-hash')
    p=commands.add_parser('opportunity');p.add_argument('campaign');p.add_argument('account');p.add_argument('json')
    p=commands.add_parser('agreement');p.add_argument('campaign');p.add_argument('account')
    p=commands.add_parser('pilot');p.add_argument('campaign');p.add_argument('account');p.add_argument('json')
    p=commands.add_parser('pilot-brief');p.add_argument('campaign');p.add_argument('account')
    commands.add_parser('pilot-metrics')
    p=commands.add_parser('score');p.add_argument('campaign');p.add_argument('account');p.add_argument('json')
    a=parser.parse_args()
    with connect(a.db) as db:
        if a.cmd=='import': result=import_campaigns(db)
        elif a.cmd=='status': result=projection(db)
        elif a.cmd=='sync': result=sync_thread(db,a.contact,json.loads(Path(a.json).read_text()));result={k:result[k] for k in ('id','status','touch_number','reply_type','snapshot_at')}
        elif a.cmd=='decide': result=decide(db,a.contact,json.loads(Path(a.json).read_text()));result={k:result[k] for k in ('id','recommended_action','next_action_at')}
        elif a.cmd=='queue': result=build_queue(db,a.date,a.capacity)
        elif a.cmd=='review':result=review_action(db,a.action_id,a.status,a.approval_hash)
        elif a.cmd=='opportunity':
            from opportunities import save_opportunity
            result=save_opportunity(campaign(a.campaign),a.account,json.loads(Path(a.json).read_text()))
        elif a.cmd=='pilot':
            from pilot_loi import save_case
            result=save_case(db,campaign(a.campaign),a.account,json.loads(Path(a.json).read_text()))
        elif a.cmd=='pilot-brief':
            from pilot_loi import load_case,render_brief
            value=load_case(db,a.campaign,slug(a.account))
            if not value:raise ValueError('Record the observed pilot case first')
            path=campaign(a.campaign)/'accounts'/slug(a.account)/'pilot-brief.md'
            path.write_text(render_brief(value));path.chmod(0o600)
            result={'path':str(path),'status':'discussion_draft','sending_enabled':False}
        elif a.cmd=='pilot-metrics':
            from pilot_loi import project,metrics
            result=metrics(project(db))
        elif a.cmd=='agreement':
            from opportunities import project_agreement,check_evidence
            folder=campaign(a.campaign)/'accounts'/slug(a.account)
            value=json.loads((folder/'opportunity.json').read_text());check_evidence(value.get('evidence'),read_sources(campaign(a.campaign)))
            if value['status'] not in {'project_identified','scope_sent'}:raise ValueError('Identify the actual project before generating an agreement')
            file=folder/'project-agreement.md';file.write_text(project_agreement(value));result={'path':str(file),'status':'draft_only'}
        elif a.cmd=='score':
            from scoring import score_fit
            folder=campaign(a.campaign)/'accounts'/slug(a.account);brief=json.loads((folder/'research.json').read_text());v=json.loads(Path(a.json).read_text())
            result=score_fit(v,[f['id'] for f in brief['facts']],brief.get('engine','technical_contract'));write_json(folder/'fit.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:raise SystemExit(str(exc))
