"""Separate contract and facility progress. Recording status never performs an action."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from research import read_sources, write_json, slug
import json
import re

CONTRACT = ["discovery", "conversation", "project_identified", "scope_sent", "signed", "paid", "delivering", "complete", "closed"]
API = ["product_identified", "data_gap_verified", "contacted", "product_conversation", "api_evaluation", "commercial_discussion", "integration", "customer", "closed"]
FACILITY = ["contact", "conversation", "visit_observe", "read_only_data", "offline_analysis", "human_approved_recommendations", "bounded_closed_loop_recovery", "deployed", "recurring_customer", "closed"]


def payment_plan(fee, uncertain=False):
    amount = Decimal(str(fee))
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Fee must be a positive amount")
    proportions = [Decimal('1')] if amount < 3000 and not uncertain else [Decimal('.5'), Decimal('.5')] if amount <= 10000 and not uncertain else [Decimal('.4'), Decimal('.3'), Decimal('.3')]
    names = ['On signing'] if len(proportions) == 1 else ['On signing', 'On delivery'] if len(proportions) == 2 else ['On signing', 'Intermediate deliverable', 'Final delivery']
    parts = [(amount*p).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) for p in proportions]
    parts[-1] = amount-sum(parts[:-1])
    return [{"milestone": name, "amount": str(part)} for name,part in zip(names,parts)]


def check_evidence(evidence, sources):
    if not evidence:
        raise ValueError("Opportunity changes need an observed reply, call note or user-confirmed fact")
    for e in evidence:
        if e.get("source_id") not in sources or not e.get("quote") or e["quote"] not in sources[e["source_id"]]["text"]:
            raise ValueError("Opportunity evidence must trace to a captured source")


def save_opportunity(path, account, value):
    engine = value.get("engine")
    if engine == 'wapahki_facility':
        from pilot_loi import save_case
        from state import connect
        with connect() as db:return save_case(db,path,account,value)
    if engine not in {"technical_contract", "wapahki_facility", "outagehub_api"}:
        raise ValueError("Resolve which business motion this opportunity belongs to")
    allowed = CONTRACT if engine == "technical_contract" else FACILITY if engine=="wapahki_facility" else API
    if value.get("status") not in allowed or not value.get("next_action"):
        raise ValueError("Opportunity needs a valid stage and next action")
    sources = read_sources(path); check_evidence(value.get("evidence"), sources)
    if value.get("currency") and not re.fullmatch(r"[A-Z]{3}",value["currency"]): raise ValueError("Use an explicit uppercase currency code")
    for field in ("fee","mrr"):
        if field in value and (not Decimal(str(value[field])).is_finite() or Decimal(str(value[field]))<=0): raise ValueError("Project and recurring amounts must be finite and positive")
    for payment in value.get("payments", []):
        if payment.get("status") == "funded":
            check_evidence(payment.get("evidence"), sources)
            if payment.get("currency") != value.get("currency") or not Decimal(str(payment.get("amount", 0))).is_finite() or Decimal(str(payment.get("amount", 0))) <= 0:
                raise ValueError("Funded amount must be positive")
    if engine == "technical_contract":
        if value["status"] in {"signed", "paid", "delivering", "complete"}:
            if not value.get("currency") or len(value["currency"]) != 3 or not value.get("fee"):
                raise ValueError("Signed value requires a fee and explicit currency")
            check_evidence(value.get("signature_evidence"), sources)
        if value["status"] in {"paid", "delivering", "complete"}:
            required = Decimal(payment_plan(value["fee"], value.get("uncertain", False))[0]["amount"])
            funded = sum(Decimal(str(p["amount"])) for p in value.get("payments", []) if p.get("status") == "funded")
            if funded < required:
                raise ValueError("Substantial work requires a signed agreement and funded first payment")
    elif engine == "wapahki_facility" and value["status"] in FACILITY[3:-1]:
        check_evidence(value.get("access_permission_evidence"), sources)
        if value["status"] in {"bounded_closed_loop_recovery", "deployed", "recurring_customer"}:
            check_evidence(value.get("execution_permission_evidence"), sources)
    if engine=="outagehub_api" and value["status"]=="customer":
        if not value.get("currency") or Decimal(str(value.get("mrr",0)))<=0: raise ValueError("Recurring revenue needs explicit currency and amount")
        check_evidence(value.get("subscription_evidence"),sources)
    target = path / "accounts" / slug(account)
    if not (target / "research.json").exists():
        raise ValueError("Opportunity must belong to a researched account/facility")
    write_json(target / "opportunity.json", {**value, "updated_at": datetime.now(timezone.utc).isoformat()})
    return value


def project_agreement(value):
    if value.get("engine") != "technical_contract":
        raise ValueError("Project agreements belong to contract work, not the facility learning funnel")
    required = ("project", "goal", "work", "deliverables", "timeline", "fee", "currency", "client_provides")
    if any(not value.get(k) for k in required):
        raise ValueError("Resolve the actual bounded problem, scope, currency, fee and dependencies before drafting an agreement")
    lines = [f'# Project Agreement: {value["project"]}', '', 'Draft for review', '', '## Goal', '', value['goal']]
    for label,key in [('What I’ll do','work'),('Deliverables','deliverables')]:
        lines += ['', '## '+label, ''] + ['- '+x for x in value[key]]
    lines += ['', '## Timeline', '', value['timeline'], '', '## Fee', '', f'{value["currency"]} {value["fee"]}', '', '## Payment', '']
    lines += [f'- {p["milestone"]}: {value["currency"]} {p["amount"]}' for p in payment_plan(value['fee'], value.get('uncertain',False))]
    lines += ['', '## Client provides', ''] + ['- '+x for x in value['client_provides']]
    lines += ['', 'Substantial work begins after signature and the first payment is funded.', '', 'Client signature: ____________________', 'Andrew signature: ____________________', 'Date: ____________________', '']
    return '\n'.join(lines)


def contact_release(rank, people, now=None, wait_days=3):
    now = now or datetime.now(timezone.utc)
    for p in people:
        if p.get('outcome',{}).get('type') not in {None,'not_sent','no_visible_reply'}:
            return {'status':'held_reply','reason':'A response exists at this account; handle the conversation before contacting another person'}
    if now.tzinfo is None: raise ValueError("Use timezone-aware current time")
    current = next((p for p in people if p['rank']==rank), {})
    if current.get('outcome', {}).get('sent_at'):
        return {'status':'already_sent','reason':'Use the existing thread and follow-up state'}
    if rank == 1:
        return {'status':'eligible','reason':'First ranked contact; draft approval is separate from sending'}
    previous = next((p for p in people if p['rank']==rank-1),None)
    sent_at = (previous or {}).get('outcome',{}).get('sent_at')
    if not sent_at:
        return {'status':'held_backup','reason':'Wait for the preceding ranked contact to be sent and its response window to pass'}
    due=datetime.fromisoformat(sent_at.replace('Z','+00:00')); added=0
    while added<wait_days:
        due+=timedelta(days=1)
        if due.weekday()<5:added+=1
    observed=(previous or {}).get('outcome',{}).get('checked_at')
    fresh=observed and datetime.fromisoformat(observed.replace('Z','+00:00'))>=due
    if now<due or not fresh:
        return {'status':'held_backup','eligible_after':due.isoformat(),'reason':'Wait three business days and refresh the thread before releasing the next contact'}
    return {'status':'eligible','reason':'Response window elapsed and a refreshed thread shows no visible reply'}
