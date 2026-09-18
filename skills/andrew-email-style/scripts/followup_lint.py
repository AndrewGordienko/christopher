"""Contract follow-up checks, respecting Andrew's current supplied reference.

The length ceiling follows the supplied reference. Its shared factual context
and proposed engagement window are allowed. Account routing, truthful claims and exact-copy checks remain gates.
Never sends mail.
"""
import json
import re
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo


def words(text):
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.replace('’', "'").lower())


def original_body(contact):
    snap=json.loads(contact['snapshot'] or '{}')
    return next((m.get('body','') for m in snap.get('messages',[]) if m.get('kind')=='sent'), '')


def text_findings(body, original='', scope_evidence=None):
    issues=[]
    def add(code,label):issues.append({'code':'followup_'+code,'label':label})
    ceiling=current_reference()['max_words']
    if len(body.split())>ceiling:add('length',f'Follow-up exceeds the supplied reference limit of {ceiling} words')
    normalized=' '.join(words(body));known=' '.join(words(original))
    for phrase in ['uoft student','co op in london']:
        if phrase in normalized and phrase in known:add('biography','Follow-up repeats the original introduction')
    # Andrew explicitly supplied the Automata/Anthropic/NVIDIA context, the
    # Sierra Leone motivation and a proposed 4–6 week paid engagement. These
    # are permitted; none establishes a recipient's budget or project scope.
    if re.search(r'\bguarantee(?:d|s)?\b[^.!?\n]{0,90}\bresults?\b',body,re.I):
        add('guarantee','Do not guarantee positive results; describe ownership and pace')
    if body.count('?')>1:add('questions','Follow-up has more than one question')
    if not body.strip():add('empty','A complete follow-up is required')
    if '—' in body:add('em_dash','Remove the em dash')
    return issues


@lru_cache(maxsize=1)
def current_reference():
    path=Path(__file__).resolve().parents[2]/'paid-contract-followup-editor/references/current-example.json'
    return json.loads(path.read_text())


def approved_shared_spans():
    return [words(span) for span in current_reference()['approved_shared_spans']]


def repetition_words(body):
    """Mask only exact user-approved shared passages, retaining boundaries."""
    tokens=words(body)
    for span in approved_shared_spans():
        if not span:continue
        i=0
        while i<=len(tokens)-len(span):
            if tokens[i:i+len(span)]==span:
                tokens[i:i+len(span)]=[None]
            i+=1
    return tokens


def shared_runs(rows):
    """Flag unapproved 15-word overlaps outside the supplied shared context."""
    owners=defaultdict(set);result=defaultdict(list)
    byid={r['id']:r for r in rows}
    for r in rows:
        ts=repetition_words(r.get('body') or '')
        for i in range(len(ts)-14):
            run=tuple(ts[i:i+15])
            if None not in run:owners[run].add(r['id'])
    pairs=set()
    for run,ids in owners.items():
        if len({byid[i]['company_key'] for i in ids})<2:continue
        for i in ids:
            other=next((j for j in sorted(ids,key=str) if byid[j]['company_key']!=byid[i]['company_key']),None)
            if other is None or (i,other) in pairs:continue
            pairs.add((i,other))
            result[i].append({'code':'followup_repetition','label':'A 15-word passage is shared with another company’s follow-up','other_id':other,'sequence':' '.join(run)})
    return dict(result)


def day_for(row):
    if row.get('send_at'):
        return datetime.fromisoformat(row['send_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/London')).date().isoformat()
    return row.get('queue_date') or row.get('review_on')


def table_exists(db,name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())


def saved_rows(db):
    from state import company_key
    rows=[]
    if table_exists(db,'followup_drafts'):
        for r in db.execute("SELECT f.*,c.context,c.entity_key,c.engine FROM followup_drafts f JOIN contacts c ON c.id=f.contact_id WHERE c.engine='technical_contract'"):
            r=dict(r);r.update(id='draft:'+r['contact_id']+':'+r['review_on'],company_key=company_key(r));rows.append(r)
    if table_exists(db,'relationship_plans'):
        for r in db.execute("SELECT p.*,c.context,c.entity_key,c.engine FROM relationship_plans p JOIN contacts c ON c.id=p.contact_id WHERE c.engine='technical_contract' AND p.action='FOLLOW_UP_SAME_PERSON' AND p.draft IS NOT NULL"):
            r=dict(r);draft=json.loads(r['draft'])
            if draft.get('body'):
                r.update(id='plan:'+r['account_key'],body=draft['body'],company_key=company_key(r));rows.append(r)
    for r in db.execute("SELECT s.*,c.context,c.entity_key,c.engine FROM scheduled_sends s JOIN contacts c ON c.id=s.contact_id WHERE c.engine='technical_contract' AND s.touch_number>1 AND s.body IS NOT NULL AND s.status IN ('review','approved','held','gmail_scheduled','cancel_required')"):
        r=dict(r);r.update(id='queue:'+str(r['id']),company_key=company_key(r));rows.append(r)
    return rows


def blockers(db,contact,body,day=None,action_id=None,scope_evidence=None):
    """Used at draft, queue, approval and execution boundaries, across campaigns."""
    from state import company_key
    if contact['engine']!='technical_contract':return []
    ctx=json.loads(contact['context']);scope_evidence=scope_evidence or ctx.get('followup_scope_evidence')
    issues=text_findings(body,original_body(contact),scope_evidence)
    cid=contact['id'];key=company_key(contact)
    others=[r for r in saved_rows(db) if r['contact_id']!=cid]
    candidate={'id':'candidate','company_key':key,'body':body}
    issues+=shared_runs([candidate]+others).get('candidate',[])
    if day and table_exists(db,'followup_choices'):
        chosen=db.execute('SELECT primary_contact_id FROM followup_choices WHERE account_key=? AND review_on=?',
                          (contact['engine']+':'+key,day)).fetchone()
        if chosen and chosen[0]!=cid:issues.append({'code':'followup_primary','label':'Another contact is the primary follow-up for this company on this date'})
    if day:
        for r in db.execute("SELECT s.*,c.context,c.entity_key FROM scheduled_sends s JOIN contacts c ON c.id=s.contact_id WHERE c.engine='technical_contract' AND s.touch_number>1 AND s.status IN ('review','approved','gmail_scheduled','cancel_required')"):
            r=dict(r)
            if r['id']!=action_id and r['contact_id']!=cid and company_key(r)==key and day_for(r)==day:
                issues.append({'code':'followup_company_day','label':'Two follow-ups at the same company cannot be scheduled on the same day'});break
    return issues
