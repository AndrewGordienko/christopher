"""Evidence gate for robotic-cell pilots; never infers fit from prose or sends mail."""
import hashlib
import json
from datetime import datetime

CRITERIA = ('cell_identity', 'operating', 'recurring_human_recovery',
            'software_recovery', 'observable_state', 'technical_owner', 'operational_benefit')
SUPPORTED = {'CONFIRMED', 'LIKELY'}
SKEPTIC_ANSWERS = ('specific_reason', 'problem', 'technical_plausibility',
                   'small_ask', 'founder_voice', 'routing_reply')


def validate(record, facts, facility_id):
    if not isinstance(record, dict) or record.get('schema_version') != 1:
        raise ValueError('Cell qualification needs schema_version 1')
    if record.get('status') not in {'QUALIFIED', 'POSSIBLE', 'HOLD'}:
        raise ValueError('Cell qualification requires QUALIFIED / POSSIBLE / HOLD')
    if not facility_id or record.get('facility_id') != facility_id:
        raise ValueError('Cell qualification must identify this exact facility')
    for key in ('reason', 'reviewer', 'reviewed_at', 'next_action'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError('Cell qualification needs ' + key)
    if datetime.fromisoformat(record['reviewed_at'].replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Cell qualification review needs a timezone')
    cell = record.get('cell') or {}
    findings = record.get('criteria') or {}
    score = 0
    for key in CRITERIA:
        finding = findings.get(key) or {}
        if finding.get('status') not in SUPPORTED | {'UNKNOWN'} or not finding.get('statement'):
            raise ValueError('Cell criterion needs status and statement: ' + key)
        basis = finding.get('basis', [])
        if not isinstance(basis, list) or any(i not in facts for i in basis):
            raise ValueError('Cell criterion needs known fact IDs: ' + key)
        if finding['status'] in SUPPORTED:
            if not basis:
                raise ValueError('Supported cell criterion needs evidence: ' + key)
            if not any(facts[i]['entity_id'] in {facility_id, cell.get('id')} for i in basis):
                raise ValueError('Cell evidence must connect to this facility/cell: ' + key)
            if finding['status'] == 'LIKELY' and not finding.get('inference'):
                raise ValueError('Likely cell criterion needs its inference: ' + key)
            if key == 'technical_owner' and not finding.get('person_id'):
                raise ValueError('Identify the technical owner, not only a title')
            score += 1
    if type(record.get('qualification_score')) is not int or record['qualification_score'] != score:
        raise ValueError('qualification_score must equal the number of supported criteria (0–7)')
    for key in ('physical_only', 'requires_safety_bypass'):
        if record.get(key) is not None and type(record[key]) is not bool:
            raise ValueError(key + ' must be true, false or null')
    if record.get('physical_only') is True or record.get('requires_safety_bypass') is True:
        if record['status'] != 'HOLD':
            raise ValueError('Physical-only or safety-bypass-dependent recovery must be HOLD')
    if record['status'] == 'QUALIFIED':
        if score != len(CRITERIA) or any(not isinstance(cell.get(k), str) or not cell[k].strip()
                                        for k in ('id', 'name', 'equipment', 'task')):
            raise ValueError('QUALIFIED needs all seven gates and a named cell/equipment/task')
        if record.get('physical_only') is not False or record.get('requires_safety_bypass') is not False:
            raise ValueError('Resolve physical-only work and safety-bypass dependence before qualification')
    return record


def digest(record, facts):
    return hashlib.sha256(json.dumps({'qualification': record, 'facts': facts},
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def context(brief):
    record = brief.get('cell_qualification')
    ids = {i for finding in (record or {}).get('criteria', {}).values() for i in finding.get('basis', [])}
    facts = {f['id']: f for f in brief.get('facts', []) if f['id'] in ids}
    return {'cell_qualification_required': True, 'cell_qualification': record,
            'cell_qualification_facts': facts, 'cell_facility_id': brief.get('facility', {}).get('id'),
            'cell_qualification_hash': digest(record, facts)}


def qualification_blockers(ctx):
    record = ctx.get('cell_qualification')
    facts = ctx.get('cell_qualification_facts', {})
    try:
        validate(record, facts, ctx.get('cell_facility_id'))
        if ctx.get('cell_qualification_hash') != digest(record, facts):
            raise ValueError('Cell qualification changed; refresh its evidence review')
        if record['status'] != 'QUALIFIED':
            raise ValueError('Cell is ' + record['status'] + '; research more before drafting or queueing')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return [{'code': 'cell_qualification', 'label': str(exc)}]
    return []


def review_blockers(ctx, draft_hash):
    reviews = ctx.get('outbound_reviews') or {}
    current = (reviews.get('draft_hash') == draft_hash and
               reviews.get('qualification_hash') == ctx.get('cell_qualification_hash'))
    result = []
    for key in ('thought_continuity', 'cold_email_skeptic'):
        review = reviews.get(key) or {}
        passed = current and review.get('passed') is True and all(review.get(k) for k in ('reviewer', 'reviewed_at', 'reason'))
        if key == 'cold_email_skeptic':
            passed = passed and all(isinstance(review.get('answers', {}).get(k), str) and
                                    review['answers'][k].strip() for k in SKEPTIC_ANSWERS)
        if not passed:
            result.append({'code': key, 'label': key.replace('_', ' ').capitalize() + ' review pending or stale'})
    return result


def required(ctx):
    return (ctx.get('cell_qualification_required') is True or ctx.get('engine') == 'wapahki_facility'
            or ctx.get('sender_mode') == 'wapahki_pilot' or bool(ctx.get('benchmark_hypothesis')))
