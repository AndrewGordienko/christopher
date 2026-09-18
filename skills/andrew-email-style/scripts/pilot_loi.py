"""Evidence-backed facility milestones and local pilot briefs; no sending or control."""
import copy,json,math,statistics,re
from datetime import datetime,timezone
from pathlib import Path
from research import read_sources,write_json,slug

STAGES=['research','contacted','conversation','qualified','site_visit','pilot_scoped','loi_sent','loi_negotiating','loi_signed','data_security','pilot_agreement','baseline','offline_evaluation','assisted_recovery','closed_loop_recovery','commercial_deployment','closed']
OWNERS=['technical_champion','economic_buyer','pilot_signatory','security_owner','data_owner']
QUALIFICATION=['facility','system','failure_problem','human_intervention','customer_metric','technical_approach','technical_owner','authorization_path']
FACTORS=['pilot_fit','failure_frequency','customer_value','data_accessibility','technical_champion_access','signatory_accessibility','safety_deployment_ease','speed_to_loi']
LOI_FIELDS=['company','facility','system','problem','customer_metric','pilot_objective','benchmark','customer_contribution','wapahki_contribution','pilot_path','timing','commercial_intent','binding_status']
CUSTOMER_KINDS={'technical_call','site_visit','customer_reply','signed_document','customer_confirmed_note'}

def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Milestone time needs an explicit timezone')
    return result

def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS facility_opportunities(
        campaign TEXT NOT NULL,account_id TEXT NOT NULL,stage TEXT NOT NULL,
        payload TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(campaign,account_id))''')

def field(value=None,status='unknown',evidence=None,kind=None):
    return {'value':value,'status':status,'evidence':evidence or [],'evidence_kind':kind}

def qualification(value):
    missing=[]
    for key in QUALIFICATION:
        f=value.get('qualification',{}).get(key,{})
        acceptable=f.get('status')=='confirmed' or (key=='technical_approach' and f.get('status')=='proposed')
        if not acceptable or not f.get('value') or not f.get('evidence') or (key not in {'facility','system'} and f.get('evidence_kind') not in CUSTOMER_KINDS):missing.append(key)
    champion=value.get('owners',{}).get('technical_champion',{})
    if champion.get('status')!='confirmed' or not champion.get('value'):
        if 'technical_owner' not in missing:missing.append('technical_owner')
    return {'ready_for_loi_ask':not missing,'missing':missing}

def loi_quality(value):
    doc=value.get('loi',{});fields=doc.get('fields',{})
    complete=lambda k:bool(fields.get(k,{}).get('value') and fields.get(k,{}).get('evidence'))
    if not doc.get('document_source_ids'):return None
    if all(complete(k)for k in LOI_FIELDS):return 'A'
    return 'B' if complete('facility') and complete('pilot_objective') else 'C'

def qualified_signed(value):
    return value.get('loi',{}).get('signature_status')=='executed' and loi_quality(value)=='A' and qualification(value)['ready_for_loi_ask']

def priority(value):
    assessed=value.get('loi_priority',{}).get('factors',{})
    known=[k for k in FACTORS if assessed.get(k,{}).get('rating') is not None]
    index=100*math.prod(assessed[k]['rating']/5 for k in FACTORS) if len(known)==len(FACTORS) else None
    return {'ordinal_index':round(index,2)if index is not None else None,'assessed_dimensions':len(known),'total_dimensions':len(FACTORS),'unknown_dimensions':[k for k in FACTORS if k not in known],'loi_probability':None,'interpretation':'Ordinal prioritization, not a calibrated probability; unknown dimensions are not zero.'}

def seed(brief,fit=None):
    """Public evidence supplies candidate scope, never a qualified customer problem."""
    f=brief['facility'];facts={x['id']:x for x in brief['facts']}
    basis=brief['benchmark_hypothesis']['basis'];evidence=[e for i in basis for e in facts[i]['evidence']]
    q={k:field()for k in QUALIFICATION}
    q['facility']=field(f['name'],'confirmed',evidence,'public_research')
    q['system']=field('; '.join(facts[i]['text']for i in basis),'candidate',evidence,'public_research')
    candidates={k:[]for k in OWNERS}
    from benchmarks import recipient_altitude
    for p in brief['stakeholders']:
        altitude=recipient_altitude(p['role'])
        roles=['technical_champion']if altitude in {'automation_controls','plant_operations'}else []
        if re.search(r'director|directeur|manager|vice|\bvp\b|chief|president|président|founder',p['role'],re.I):roles+=['economic_buyer','pilot_signatory']
        for role in roles:candidates[role].append({'person_id':p['id'],'name':p['name'],'role':p['role'],'status':'candidate','authority_confirmed':False,'basis':p.get('fact_ids',[]),'reason':'Role-based routing hypothesis; actual remit, willingness and authority must be established.'})
    factors={k:{'rating':None,'reason':'Requires customer/technical discovery','evidence':[]}for k in FACTORS}
    if fit and fit.get('score') is not None:
        factors['pilot_fit']={'rating':round(fit['score']/20,2),'reason':'Existing facility pilot/data fit assessment; not an LOI or procurement forecast.','evidence':evidence}
    return {'schema_version':1,'engine':'wapahki_facility','facility_id':f['id'],'company_id':brief['company']['id'],'facility_name':f['name'],'company_name':brief['company']['name'],'stage':'research',
      'case_owner':'Andrew Gordienko','next_action':'Review the primary remote-call pilot offer; first call confirms material recovery loss, customer value and the authority path.','next_action_trigger':'Andrew approves the current primary draft; pause the company outreach sequence on any reply.',
      'qualification':q,'owners':{k:field()for k in OWNERS},'owner_candidates':candidates,
      'discovery':{k:field()for k in ['failure_frequency','recovery_duration','operator_actions','logged_events','objections','site_access_owner','data_access_owner','control_access_owner']},
      'scope':{'objective':brief['pilot_value_case']['pilot_value_proposition'],'benchmark':'Intervention events, active person-minutes, recovery time and an agreed production denominator. Quantitative baseline unknown.',
        'guardrails':', '.join(x['metric'].replace('_',' ')for x in brief['benchmark_hypothesis']['plant_guardrails'])+'; confirm applicability with the plant.',
        'phases':'Read-only baseline → offline evaluation → assisted recovery → bounded automatic recovery only for mutually approved cases.',
        'facility_provides':'Proposed: technical owner, engineering context and mutually agreed site/data access, subject to security and legal approval.',
        'wapahki_provides':'Proposed: failure analysis, intervention baseline, recovery benchmark, evaluation and a bounded recovery prototype.',
        'timing':None,'commercial_terms':None,'agreed':False},
      'loi':{'signature_status':'not_requested','signed_at':None,'document_source_ids':[],'signature_evidence':[],'signatories':[],'fields':{}},
      'permissions':{},'milestones':[],'loi_priority':{'factors':factors},'updated_at':datetime.now(timezone.utc).isoformat()}

def validate(value,sources,now=None):
    from opportunities import check_evidence
    now=now or datetime.now(timezone.utc)
    if value.get('schema_version')!=1 or value.get('engine')!='wapahki_facility' or value.get('stage')not in STAGES:raise ValueError('Resolve the versioned Wapahki facility stage')
    if not all(value.get(k)for k in ('facility_id','company_id','facility_name','company_name')):raise ValueError('Name the company and exact facility')
    if value['stage']!='closed' and not all(value.get(k)for k in ('case_owner','next_action')):raise ValueError('Every active opportunity needs an owner and next action')
    if value['stage']!='closed' and not(value.get('next_action_due')or value.get('next_action_trigger')):raise ValueError('Give the next action a due date or explicit trigger')
    for group in ('qualification','owners','discovery'):
        for key,f in value.get(group,{}).items():
            if f.get('status')not in {'unknown','candidate','proposed','confirmed'}:raise ValueError('Keep candidate and confirmed fields separate')
            if f.get('status')=='unknown' and f.get('value')is not None:raise ValueError('Unknown fields cannot assert a value')
            if f.get('status')!='unknown':
                if f.get('value')is None:raise ValueError('An assessed field needs a value')
                check_evidence(f.get('evidence'),sources)
                if f['status']=='confirmed' and not(group=='qualification' and key in {'facility','system'}) and f.get('evidence_kind')not in CUSTOMER_KINDS:raise ValueError('Public title/equipment evidence cannot confirm pain, KPI, ownership or authority')
    for k in OWNERS:
        if k not in value.get('owners',{}):raise ValueError('Track unknown owner: '+k)
    for key,item in value.get('loi_priority',{}).get('factors',{}).items():
        if key not in FACTORS:raise ValueError('Unknown LOI prioritization dimension')
        if item.get('rating')is not None:
            if type(item['rating'])not in (int,float)or not 0<=item['rating']<=5 or not item.get('reason'):raise ValueError('LOI priorities are explained 0–5 ordinal judgments')
            check_evidence(item.get('evidence'),sources)
    milestones=value.get('milestones',[])
    for m in milestones:
        if m.get('stage')not in STAGES or instant(m['at'])>now:raise ValueError('Record actual, non-future milestones')
        check_evidence(m.get('evidence'),sources)
        if m['stage']in {'conversation','qualified','site_visit','pilot_scoped'}and m.get('kind')not in CUSTOMER_KINDS:raise ValueError('A public page is not a customer conversation or qualified pilot')
        if m['stage']in {'contacted','loi_sent'}and m.get('kind')!='sent_mail':raise ValueError('Scheduled/draft messages are not sent milestones')
        if m['stage']in {'loi_signed','pilot_agreement'}and m.get('kind')!='signed_document':raise ValueError('Verbal interest is not a signed document')
        expected={'baseline':'telemetry_observation','offline_evaluation':'evaluation_result','assisted_recovery':'deployment_observation','closed_loop_recovery':'deployment_observation','commercial_deployment':'deployment_observation'}
        if m['stage']in expected and m.get('kind')!=expected[m['stage']]:raise ValueError('Record observed pilot execution, not an intended phase')
    if value['stage']!='research' and not any(m['stage']==value['stage']for m in milestones):raise ValueError('Stage needs a matching observed milestone')
    required={'qualified','pilot_scoped','loi_sent','loi_negotiating','pilot_agreement','baseline','offline_evaluation','assisted_recovery','closed_loop_recovery','commercial_deployment'}
    if (value['stage']in required or any(m['stage']in required for m in milestones)) and not qualification(value)['ready_for_loi_ask']:raise ValueError('Resolve LOI qualification: '+', '.join(qualification(value)['missing']))
    doc=value.get('loi',{})
    if doc.get('signature_status')not in {'not_requested','draft','sent','negotiating','executed','declined'}:raise ValueError('Resolve actual LOI signature status')
    doc_ids=set(doc.get('document_source_ids',[]))
    if not doc_ids<=set(sources):raise ValueError('LOI must reference captured documents')
    for f in doc.get('fields',{}).values():
        if f.get('value'):
            check_evidence(f.get('evidence'),sources)
            if not all(e['source_id']in doc_ids for e in f['evidence']):raise ValueError('LOI quality must be in the document, not inferred from a separate call')
    named_facility=doc.get('fields',{}).get('facility',{}).get('value')
    if named_facility and value['facility_name'].casefold() not in str(named_facility).casefold():raise ValueError('LOI scope must name this exact facility, not another site')
    if doc.get('signature_status')=='executed':
        if not doc_ids or not doc.get('signatories') or not doc.get('signed_at')or instant(doc['signed_at'])>now:raise ValueError('Executed LOI needs signatories, document and actual signature date')
        check_evidence(doc.get('signature_evidence'),sources)
        if not all(e['source_id']in doc_ids for e in doc['signature_evidence']):raise ValueError('Signature evidence must come from the executed document')
        if not any(m['stage']=='loi_signed'and m['kind']=='signed_document'and instant(m['at'])==instant(doc['signed_at'])for m in milestones):raise ValueError('Executed LOI needs matching signature milestone')
    if value['stage']=='loi_signed' and doc.get('signature_status')!='executed':raise ValueError('An unsigned LOI is not signed')
    if qualified_signed(value) and value['owners']['pilot_signatory'].get('status')!='confirmed':raise ValueError('Qualified signed LOI needs confirmed pilot-signatory authority')
    for permission in value.get('permissions',{}).values():
        if permission.get('authorized')is True:
            check_evidence(permission.get('evidence'),sources)
            if permission.get('kind')!='explicit_permission' or not permission.get('scope'):raise ValueError('Permission needs explicit scope; intent alone is insufficient')
    access_stages={'baseline','offline_evaluation','assisted_recovery','closed_loop_recovery','commercial_deployment'}
    if any(m['stage']=='pilot_agreement'for m in milestones):
        agreement=value.get('pilot_agreement',{})
        if agreement.get('signature_status')!='executed':raise ValueError('Pilot agreement must be a separately executed definitive agreement')
        check_evidence(agreement.get('signature_evidence'),sources)
    if value['stage']in access_stages:
        if not any(m['stage']=='pilot_agreement'for m in milestones):raise ValueError('Resolve the definitive pilot agreement before production-data work')
        if value.get('permissions',{}).get('data',{}).get('authorized')is not True:raise ValueError('An LOI is not data-access permission')
    if value['stage']in {'assisted_recovery','closed_loop_recovery'}:
        permission='control'if value['stage']=='closed_loop_recovery'else 'assisted'
        if value.get('permissions',{}).get(permission,{}).get('authorized')is not True:raise ValueError('Resolve explicit scoped '+permission+' permission')
    if value['stage']=='commercial_deployment':
        mode=value.get('deployment_mode')
        if mode not in {'read_only','offline','assisted','closed_loop'}:raise ValueError('Name the actual commercial deployment mode')
        if mode in {'assisted','closed_loop'} and value.get('permissions',{}).get('control'if mode=='closed_loop'else 'assisted',{}).get('authorized')is not True:raise ValueError('Commercial deployment needs permission for its actual mode')
        check_evidence(value.get('payment_evidence'),sources)
        check_evidence(value.get('deployment_evidence'),sources)
        check_evidence(value.get('measured_result_evidence'),sources)
    return value

def load_case(db,campaign,account):
    schema(db);row=db.execute('SELECT payload FROM facility_opportunities WHERE campaign=? AND account_id=?',(campaign,account)).fetchone()
    return json.loads(row['payload'])if row else None

def next_step(value):
    gate=qualification(value);stage=value['stage']
    if stage in {'conversation','qualified','site_visit','pilot_scoped'}:
        return {'step':'prepare_pilot_brief_and_loi_ask'if gate['ready_for_loi_ask']else 'complete_pilot_qualification','owner':value['case_owner'],'missing':gate['missing'],
            'instruction':'Prepare/update the pilot brief now. '+('Confirm it captures the discussion, then propose the counsel-prepared LOI; skip unnecessary meetings.'if gate['ready_for_loi_ask']else 'Resolve these gaps in the existing thread or one focused call/visit; do not request an LOI yet.')}
    return {'step':'advance_pilot_opportunity','owner':value.get('case_owner'),'instruction':value.get('next_action'),'trigger':value.get('next_action_due')or value.get('next_action_trigger')}

def render_brief(value):
    if not any(m['stage']in {'conversation','site_visit'}and m.get('outcome')=='positive'for m in value.get('milestones',[])):raise ValueError('Prepare the pilot brief after an observed positive technical conversation or visit')
    q=value['qualification'];scope=value.get('scope',{});gate=qualification(value)
    def text(key):
        f=q.get(key,{})
        return f.get('value')or 'To establish with the facility'
    lines=[f'# Wapahki × {value["facility_name"]}','','Discussion draft · proposed scope, not an agreement or permission','','**Problem and system**',text('system'),text('failure_problem'),text('human_intervention'),'',
      '**Customer value / pilot objective**',scope.get('objective')or text('technical_approach'),'Customer measure: '+text('customer_metric'),'',
      '**Initial benchmark**',scope.get('benchmark')or 'Intervention events/minutes, recovery time and an agreed production denominator; quantitative baseline to establish.',
      'Guardrails: '+(scope.get('guardrails')or 'Agree throughput, quality and safety measures for this operation.'),'',
      '**Proposed path**',scope.get('phases')or 'Read-only baseline → offline evaluation → assisted recovery → bounded recovery only where explicitly authorized.','',
      '**Contributions**','Facility: '+(scope.get('facility_provides')or 'Technical owner, engineering context and mutually agreed access, subject to security/legal approval.'),
      'Wapahki: '+(scope.get('wapahki_provides')or 'Baseline, failure taxonomy, recovery benchmark, evaluation and a bounded prototype.'),'',
      '**Timing and commercial terms**',scope.get('timing')or 'Indicative start and duration to agree.',scope.get('commercial_terms')or 'Pilot pricing/cost responsibilities and potential commercial deployment to discuss; no fee or free-pilot commitment assumed.','',
      '**Next step**','Align this brief, then propose a short pilot LOI subject to technical, security, legal and commercial terms.'if gate['ready_for_loi_ask']else 'Resolve: '+', '.join(gate['missing'])+'. This is not yet qualified for an LOI ask.','',
      'Site data, permitted use and model-improvement rights remain separate matters for agreed terms. No data or control permission is implied.','']
    return '\n'.join(lines)

def save_case(db,path,account,value):
    account=slug(account);folder=path/'accounts'/account
    brief=json.loads((folder/'research.json').read_text())
    if value.get('facility_id')!=brief['facility']['id']or value.get('company_id')!=brief['company']['id']:raise ValueError('Pilot belongs to this exact researched facility/company')
    validate(value,read_sources(path));schema(db)
    old=load_case(db,path.name,account)
    if old:
        for event in old.get('milestones',[]):
            if event not in value.get('milestones',[]):raise ValueError('Preserve observed milestone history; record corrections explicitly')
    value=copy.deepcopy(value);value['updated_at']=datetime.now(timezone.utc).isoformat()
    generated=None
    positive=any(m['stage']in {'conversation','site_visit'}and m.get('outcome')=='positive'for m in value.get('milestones',[]))
    if positive:
        generated=render_brief(value)
        if old and value['stage']in {'conversation','qualified','site_visit','pilot_scoped'} and value.get('next_action')==old.get('next_action'):
            value['next_action']=next_step(value)['instruction']
            value['next_action_due']=value['updated_at']
            value.pop('next_action_trigger',None)
    with db:db.execute('INSERT OR REPLACE INTO facility_opportunities VALUES(?,?,?,?,?)',(path.name,account,value['stage'],json.dumps(value,ensure_ascii=False),value['updated_at']))
    write_json(folder/'pilot-opportunity.json',value)
    if generated:
        p=folder/'pilot-brief.md';p.write_text(generated);p.chmod(0o600)
    return {'case':value,'qualification':qualification(value),'loi_quality':loi_quality(value),'qualified_signed':qualified_signed(value),'priority':priority(value),'next_step':next_step(value),'brief_generated':generated is not None,'sending_enabled':False}

def project(db):
    schema(db);result=[]
    for row in db.execute('SELECT * FROM facility_opportunities ORDER BY campaign,account_id'):
        v=json.loads(row['payload']);v.update(campaign=row['campaign'],account_id=row['account_id'])
        first=db.execute('SELECT MIN(first_sent_at) FROM contacts WHERE campaign=? AND account_id=?',(row['campaign'],row['account_id'])).fetchone()[0]
        v['first_contact_at']=first
        if v['stage']=='research' and first:v['stage']='contacted'
        v.update(qualification_state=qualification(v),loi_quality=loi_quality(v),qualified_signed=qualified_signed(v),priority_summary=priority(v),recommended_next_step=next_step(v))
        v['pilot_brief']=render_brief(v)if any(m['stage']in {'conversation','site_visit'}and m.get('outcome')=='positive'for m in v.get('milestones',[]))else None
        result.append(v)
    return result

def metrics(cases,now=None):
    now=now or datetime.now(timezone.utc)
    def date(v,key):
        if key=='first_contact':return v.get('first_contact_at')
        if key=='signed':return v.get('loi',{}).get('signed_at')if qualified_signed(v)else None
        return min((m['at']for m in v.get('milestones',[])if m['stage']==key),default=None)
    durations={}
    for start,end in [('first_contact','qualified'),('conversation','pilot_scoped'),('pilot_scoped','loi_sent'),('loi_sent','signed'),('first_contact','signed')]:
        completed=[];open_ages=[];inconsistent=0;closed=0
        for v in cases:
            a,b=date(v,start),date(v,end)
            if not a:continue
            if not b and v.get('stage')=='closed':closed+=1;continue
            days=((instant(b)if b else now)-instant(a)).total_seconds()/86400
            if days<0:inconsistent+=1;continue
            (completed if b else open_ages).append(days)
        durations[start+'_to_'+end]={'median_days':round(statistics.median(completed),2)if completed else None,'completed':len(completed),'open':len(open_ages),'closed_without_conversion':closed,'median_open_age_days':round(statistics.median(open_ages),2)if open_ages else None,'inconsistent_dates':inconsistent}
    signed=[v for v in cases if v.get('loi',{}).get('signature_status')=='executed']
    qualified=[v for v in cases if date(v,'qualified')]
    contacted=[v for v in cases if date(v,'first_contact')]
    good=[v for v in cases if qualified_signed(v)]
    live=lambda v:any(m['stage']=='baseline'for m in v.get('milestones',[]))
    paid=lambda v:any(m['stage']=='commercial_deployment'for m in v.get('milestones',[]))and bool(v.get('payment_evidence'))
    live_cases=[v for v in cases if live(v)]
    def rate(cohort,predicate):
        n=sum(bool(predicate(v))for v in cohort);return {'numerator':n,'denominator':len(cohort),'rate':round(n/len(cohort),4)if cohort else None}
    return {'as_of':now.isoformat(),'cohort':'All recorded facility cases; contact clock starts at observed outbound, not scheduling. Completed medians include sample counts and open ages.','facilities':len(cases),'qualified_opportunities':len(qualified),'facilities_contacted':len(contacted),'signed_lois_by_quality':{k:sum(loi_quality(v)==k for v in signed)for k in ['A','B','C']},'qualified_signed_lois':len(good),'live_pilots':len(live_cases),'paid_deployments':sum(paid(v)for v in cases),'cycle_times':durations,
      'conversion':{'signed_per_qualified':rate(qualified,qualified_signed),'signed_per_contacted':rate(contacted,qualified_signed),'loi_to_live_pilot':rate(good,live),'live_pilot_to_paid':rate(live_cases,paid)}}
