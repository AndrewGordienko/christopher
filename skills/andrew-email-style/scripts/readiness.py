"""Blocking review checks. A recommendation is never authorization to send."""
import hashlib
import re
from pathlib import Path

def fingerprint(subject, body):
    return hashlib.sha256((subject+'\n\n'+body).encode()).hexdigest()

def language_findings(body):
    """Known regressions only. An empty list is not a grammar-review pass."""
    patterns = [
        (r'London, UK\s+working', 'Missing closing comma after London, UK'),
        (r'interested me as somewhere', 'Non-idiomatic interested me as somewhere construction'),
        (r'somewhere\s+(?:catching|detecting|better predictions)', 'Missing relative-clause connector after somewhere'),
        (r'alongside my current work and attached', 'Broken coordination between future work and past attachment'),
        (r'use that planning work on preventing', 'Use the planning work to help prevent failures'),
        (r'if there[’\x27]s something you need more[.!?]', 'Incomplete comparison: something else the team needs more'),
    ]
    return [{'code':'language_pattern','label':label} for pattern,label in patterns if re.search(pattern,body,re.I)]

def check_states(context, subject, body):
    digest=fingerprint(subject or '',body or '')
    review=context.get('final_checks') or {}
    current=review.get('draft_hash')==digest and bool(review.get('reviewed_at')) and bool(review.get('reviewer'))
    states={key:('passed' if current and review.get(key,{}).get('passed') is True else 'stale after edit' if review and not current else 'pending') for key in ('voice','grammar','facts')}
    external=context.get('external_critic_review') or {}
    required=context.get('external_critic_required') is True or bool(external)
    if not required: states['external']='not enabled'
    elif external.get('after_hash')!=digest: states['external']='stale after edit' if external else 'pending'
    elif external.get('status')=='reviewed' and re.fullmatch(r'https://chatgpt\.com/(?:g/[^/?#]+/)?c/[^/?#]+(?:[?#].*)?',external.get('chat_url','')) and external.get('observed_at') and external.get('feedback'): states['external']='passed'
    else: states['external']='pending'
    return states

def blockers(context, subject=None, body=None, touch=1):
    subject=context.get('subject','') if subject is None else subject
    body=context.get('body','') if body is None else body
    result=[]
    def add(code,label): result.append({'code':code,'label':label})
    if not context.get('email') or context.get('email_status')!='verified': add('email','Email needs verification')
    if not context.get('timezone') or context.get('timezone_uncertain'): add('timezone','Recipient timezone needs confirmation')
    subject=subject or '';body=body or ''
    digest=fingerprint(subject,body)
    from cell_qualification import required, qualification_blockers, review_blockers
    if required(context):
        result.extend(qualification_blockers(context))
        result.extend(review_blockers(context, digest))
    if re.search(r'attach(?:ed|ing|ment)[^\n.!?]*?(?:resume|résumé|\bCV\b)|(?:resume|résumé|\bCV\b)[^\n.!?]*?attach(?:ed|ing|ment)',body,re.I):
        valid=False
        for a in context.get('attachments',[]):
            path=Path(a.get('path',''))
            if a.get('draft_hash')==digest and a.get('kind')=='resume' and path.is_file() and a.get('sha256')==hashlib.sha256(path.read_bytes()).hexdigest(): valid=True
        if not valid: add('resume','Resume needs attachment')
    if context.get('factual_review_hash')!=digest or context.get('facts_supported') is not True: add('facts','Current draft needs factual review')
    states=check_states(context,subject,body)
    for key,title in [('facts','Fact'),('grammar','Grammar/idiom'),('voice','Voice')]:
        if states[key]!='passed' and not any(x['code']==key for x in result): add(key,title+' check '+states[key])
    if states['external'] not in {'passed','not enabled'}: add('external_critic','External critic '+states['external'])
    result.extend(language_findings(body))
    if touch==1 and context.get('already_contacted'): add('contacted','Recipient already contacted')
    return result
