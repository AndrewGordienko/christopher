"""Codex-driven missions and a curated local review API; no sending capability."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sys
from research import WORKSPACE, campaign, read_sources, validate_brief, write_json, slug
from sender import route_sender_mode


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def plan_mission(goal, overrides=None):
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("A mission needs a plain-English goal")
    text = goal.casefold()
    count = re.search(r"\b(\d+)\s+(?:[a-z]+\s+){0,5}(?:organizations?|organisations?|companies|facilities)\b", text)
    people = re.search(r"\b(\d+)\s+(?:best\s+)?(?:people|contacts|persons)\b", text)
    project = "OutageHub" if "outagehub" in text else "Wapahki" if "wapahki" in text or re.search(r"morrow.*(?:pilot|robot|cell)|recycl|retread|robot.*facilit", text) else "personal technical work"
    objective = "technical_contract"
    if project == "OutageHub":
        objective = "acquisition" if re.search(r"acquir|acquisition", text) else "api_sales"
    elif re.search(r"\binvestors?\b|fundrais|\bvc\b", text):
        objective = "investor"
    elif re.search(r"\bpilot\b|design.partner", text):
        objective = "pilot"
    elif re.search(r"\bvisit\b|learn.{0,20}factor", text):
        objective = "research_visit"
    plan = {"goal": goal.strip(), "target_accounts": int(count[1]) if count else 1,
            "people_per_account": int(people[1]) if people else 3, "project": project,
            "objective": objective, "mode": "draft_only", "executor": "Codex chat with current web/Gmail/Apollo tools",
            "subject_candidates": 8, "body_policy": "Preserve a current task draft; otherwise generate close candidates",
            "enrichment_policy": "Research and rank first; enrich only final selected people",
            "schedule_policy": "Recipient-local recommendation only", "created_at": datetime.now(timezone.utc).isoformat()}
    if overrides:
        allowed = {"target_accounts", "people_per_account", "project", "objective", "qualification_criteria", "personas", "title", "engine", "subvertical", "geography", "wapahki_mode", "vertical"}
        if set(overrides)-allowed:
            raise ValueError("Unsupported mission override")
        plan.update(overrides)
    if type(plan["target_accounts"]) is not int or not 1 <= plan["target_accounts"] <= 1000:
        raise ValueError("Resolve the number of organizations")
    if type(plan["people_per_account"]) is not int or not 1 <= plan["people_per_account"] <= 3:
        raise ValueError("Research and rank up to three people per account")
    if plan["project"]=="OutageHub" and plan["objective"]=="technical_contract": plan["objective"]="api_sales"
    if plan["project"]=="Wapahki" and plan["objective"]=="technical_contract": plan["objective"]="workflow_conversation"
    plan["engine"] = plan.get("engine") or ("outagehub_api" if plan["project"]=="OutageHub" else "wapahki_facility" if plan["project"]=="Wapahki" else "technical_contract")
    from scoring import POLICIES
    if plan["engine"] not in POLICIES: raise ValueError("Unknown workspace")
    plan["policy"] = POLICIES[plan["engine"]]
    plan["unit"] = plan["policy"]["unit"]
    if re.search(r"tire|tyre|retread", text):
        plan["subvertical"] = "tire_retreading" if "retread" in text and not re.search(r"tire.*recycl|tyre.*recycl", text) else "tire_recycling"
    plan["sender_mode"] = route_sender_mode(plan)
    if plan["engine"] == "wapahki_facility" and plan["objective"] != "investor":
        recycling = bool(re.search(r"recycl|retread|\bmrf\b", text)) or plan.get("subvertical") in {"material_recovery", "tire_recycling", "tire_retreading", "mixed_recycling"}
        plan.setdefault("vertical", "recycling" if recycling else "unresolved")
        plan.setdefault("wapahki_mode", "pilot" if recycling and not re.search(r"\bdiscovery\b|\bdiscover how\b", text) else "discovery")
        if plan["wapahki_mode"] not in {"pilot", "discovery"}:
            raise ValueError("Wapahki mode must be pilot or discovery")
        if plan["vertical"] != "recycling" and plan["wapahki_mode"] == "pilot":
            plan["wapahki_mode"] = "discovery"
            plan["promotion_required"] = "Resolve a reusable adapter from sourced discovery observations before pilot outreach"
        plan["benchmark_schema_version"] = 1
        plan["commercial_objective"] = "Minimize first contact to qualified signed A pilot LOI without reducing scope quality"
        plan["loi_reference"] = "references/wapahki-loi.md"
        if plan["wapahki_mode"] == "discovery" and plan["objective"] in {"pilot", "design_partner"}:
            plan["eventual_objective"] = plan["objective"]
            plan["objective"] = "workflow_conversation"
        plan['cell_qualification_required'] = True
        plan['qualification_score_required'] = '0–7 evidence coverage; all seven supported gates required; not a probability'
        plan['volume_policy'] = 'Research ceiling only; never fill a send quota with weak cells'
        plan["first_milestone"] = "Qualify one operating cell and its repeatable human recovery before any email"
        plan["first_touch_offer"] = "One cell, agreed passive fault/action/restored-state observation, repeated recovery sequences, then separately authorized evaluation of one suitable safe case"
        plan["sender_mode"] = "wapahki_pilot" if plan["wapahki_mode"] == "pilot" else "factory_learning"
    plan.setdefault("personas", ["Research Director", "Chief Scientist", "ML Lead"] if objective == "technical_contract" else ["Role owning the stated problem", "Practical technical champion", "Relevant senior sponsor"])
    plan["steps"] = ["discover_accounts", "research_and_qualify", "discover_and_rank_people", "enrich_selected_contacts", "resolve_recipient_and_sender_context", "research_current_trigger", "retrieve_sent_and_outcomes", "draft_and_rank_subject_body", "recommend_local_send_time", "review_queue"]
    if plan.get("benchmark_schema_version"):
        plan['steps'] = ['discover_deployed_cells', 'research_cell_recovery_evidence', 'qualify_cell',
                         'identify_cell_owner', 'research_recipient', 'enrich_selected_contacts',
                         'retrieve_sent_and_outcomes', 'morrow_email_strategy', 'andrew_outbound_voice',
                         'thought_continuity_review', 'cold_email_skeptic', 'final_language_and_fact_checks',
                         'recommend_local_send_time', 'review_queue']
    return plan


def create_mission(goal, campaign_name=None, overrides=None, root=WORKSPACE):
    plan = plan_mission(goal, overrides)
    name = campaign_name or (slug(goal)[:60].rstrip("-") + "-" + hashlib.sha256(goal.encode()).hexdigest()[:8])
    path = campaign(name, goal, root)
    existing = load(path / "mission.json")
    if existing:
        if existing["goal"] != plan["goal"]:
            raise ValueError("Mission already exists with another goal; choose a new name")
        return {"path": str(path), "mission": existing, "resumed": True}
    write_json(path / "mission.json", plan)
    return {"path": str(path), "mission": plan, "resumed": False}


def draft_hash(subject, body):
    return hashlib.sha256((subject + "\n\n" + body).encode()).hexdigest()


def selected_draft(folder):
    joint = load(folder / "subject-body-ranking.json", {})
    if joint.get("selected"):
        return joint["selected"]
    ranking = load(folder / "ranking.json", {})
    return next((c for c in load(folder / "candidates.json", []) if c["id"] == ranking.get("winner")), None)


def validate_contact(contact, sources, expected):
    if not contact:
        return None
    if contact.get("person_id") != expected["id"] or contact.get("name") != expected["name"]:
        raise ValueError("Contact identity does not match researched stakeholder")
    source = sources.get(contact.get("source_id"))
    if not source:
        raise ValueError("Contact must trace to a captured provider/public source")
    if contact.get("email") and contact["email"] not in source["text"]:
        raise ValueError("Contact address is absent from captured source")
    if contact.get("email_status") == "verified":
        if "apollo" not in source["tool"].casefold() or "verified" not in source["text"].casefold():
            raise ValueError("Provider verification must occur in actual Apollo evidence")
    if source["tool"] == "Apollo API":
        from apollo import normalize_contact
        response = json.loads(source["text"])
        raw = response.get("person", {})
        if raw.get("email") != contact.get("email") or raw.get("email_status") != contact.get("email_status"):
            raise ValueError("Email and verification must belong to the matched Apollo person")
        from apollo import normalize_name
        if normalize_name(raw.get("name")) != normalize_name(expected["name"]):
            raise ValueError("Apollo evidence belongs to a different person")
    return contact


def review_campaign(path):
    meta = load(path / "campaign.json", {})
    plan = load(path / "mission.json", {})
    sources = read_sources(path)
    accounts = []
    for f in sorted(path.glob("accounts/*/research.json")):
        brief = load(f); validate_brief(brief, sources); folder = f.parent
        contacts = []
        for p in sorted(brief["stakeholders"], key=lambda p:p["rank"]):
            person = folder / slug(p["id"])
            draft = selected_draft(person)
            contact_error = None
            try:
                contact = validate_contact(load(person / "contact.json"), sources, p)
            except ValueError as exc:
                # Keep an incomplete account reviewable without presenting its address
                # as verified or preventing access to unrelated campaign drafts.
                contact, contact_error = None, str(exc)
            email_status = "identity_unresolved" if contact_error else (contact or {}).get("email_status", "not_enriched")
            if (contact or {}).get("email_usable") is False:
                email_status = "identity_unresolved"
            scheduling = load(person / "schedule.json", {})
            if scheduling.get("source_id") and scheduling["source_id"] not in sources:
                raise ValueError("Timezone must trace to a captured location source")
            history = load(person / "retrieval.json", {})
            review = load(person / "review.json", {})
            fingerprint = draft_hash(draft.get("subject", ""), draft["body"]) if draft else None
            stale = bool(review and review.get("base_hash") != fingerprint)
            subject = review.get("subject", (draft or {}).get("subject", ""))
            body = review.get("body", (draft or {}).get("body", ""))
            from readiness import blockers
            critique=load(person / "critic.json",{}).get((draft or {}).get("id"),{})
            ready_context={"email":(contact or {}).get("email"),"email_status":email_status,"timezone":scheduling.get("timezone"),"timezone_uncertain":scheduling.get("assumed_office_location",False),"subject":subject,"body":body,"attachments":load(person / "attachments.json",[]),"facts_supported":critique.get("facts_supported") is True and not critique.get("reject"),"factual_review_hash":fingerprint,"already_contacted":load(person / "mailbox-check.json",{}).get("already_contacted",False)}
            contact_issues = [{'code':'contact_identity','label':contact_error}] if contact_error else []
            final_checks=load(person / 'final-checks.json',{})
            external=load(person / 'external-critic.json',{})
            ready_context.update(final_checks=final_checks,
                factual_review_hash=final_checks.get('draft_hash'),
                facts_supported=final_checks.get('facts',{}).get('passed') is True,
                external_critic_review=external,external_critic_required=bool(external),
                timezone_source=scheduling.get('timezone_source'),timezone_source_id=scheduling.get('source_id'),
                schedule_policy=scheduling.get('policy'),send_at=scheduling.get('recommended_send_utc'))
            if brief.get('engine') == 'wapahki_facility':
                from cell_qualification import context as cell_context
                ready_context.update(cell_context(brief), outbound_reviews=load(person / 'outbound-reviews.json', {}))
            from readiness import check_states
            checks=check_states(ready_context,subject,body)
            from scheduling import validate_send_time
            schedule_issues=validate_send_time(ready_context,scheduling.get('recommended_send_utc')) if draft else []
            evidence_ids = set(p.get("fact_ids", []))
            source_ids = {e["source_id"] for fact in brief["facts"] if fact["id"] in evidence_ids for e in fact["evidence"]}
            if contact: source_ids.add(contact["source_id"])
            contacts.append({"id": p["id"], "name": p["name"], "role": p["role"], "rank": p["rank"], "reason": p["reason"],
                             "email": (contact or {}).get("email"), "email_status": email_status, "contact_error": contact_error,
                             "provider_email_status": (contact or {}).get("email_status"),
                             "contact_provider": (contact or {}).get("email_verification_source"), "contact_observed_at": (contact or {}).get("observed_at"),
                             "subject": subject, "body": body, "base_hash": fingerprint,
                             "draft_status": ("review_previous_edits" if stale else review.get("status", "draft_ready" if draft else "pending")),
                             "readiness_context":ready_context,"blockers":contact_issues+blockers(ready_context)+schedule_issues,"subject_alternatives":[x.get("subject",x.get("text")) for x in load(person / "subject-candidates.json",[])],"thread_check":load(person / "mailbox-check.json",{}),"schedule": scheduling, "outcome": {"type": "not_sent"},
                             "history": [{"date": r.get("sent_at"), "subject": r.get("subject"), "type": r.get("context", {}).get("type"), "source":r.get("source"),"reason":r.get("selection_reason") or ", ".join(r.get("match_reasons",[]))} for r in history.get("voice_examples", [])],
                             "checks": {**checks,"fact":checks['facts']},
                             "sender_context": history.get("sender_context", {}),
                             "sources": [{"id": sid, "url": sources[sid]["url"], "observed_at": sources[sid]["observed_at"]} for sid in sorted(source_ids)]})
        all_source_ids = {e["source_id"] for fact in brief["facts"] for e in fact["evidence"]}
        accounts.append({"id": folder.name, "name": brief.get("facility", brief["company"])["name"], "parent_company": brief["company"]["name"], "facility": brief.get("facility"), "opportunity": load(folder / "opportunity.json"), "fit": load(folder / "fit.json"), "strategy": brief["message_strategy"], "domain": brief["company"].get("domain"),
                         "industry": brief["company"].get("industry"), "qualification": brief["qualification"],
                         "cell_qualification": brief.get('cell_qualification'),
                         "benchmark_hypothesis": brief.get("benchmark_hypothesis"),
                         "outagehub_integration": brief.get("outagehub_integration"),
                         "outagehub_score": brief.get("outagehub_score"),
                         "pilot_value_case": brief.get("pilot_value_case"),
                         "pilot_state": brief.get("pilot_state"),
                         "pilot_opportunity": load(folder / "pilot-opportunity.json"),
                         "why_now": brief["message_strategy"].get("why_now"), "hypotheses": brief["hypotheses"],
                         "facts": [{"text": f["text"], "id": f["id"], "sources": [e["source_id"] for e in f["evidence"]]} for f in brief["facts"]],
                         "sources": [{"id": sid, "url": sources[sid]["url"], "observed_at": sources[sid]["observed_at"]} for sid in sorted(all_source_ids)],
                         "contacts": contacts})
    people = [p for a in accounts for p in a["contacts"]]
    return {"id": path.name, "name": plan.get("title", meta.get("name", path.name)), "goal": plan.get("goal", meta.get("goal")),
            "mode": "draft_only", "engine": plan.get("engine", "technical_contract"), "mission": plan, "accounts": accounts,
            "counts": {"companies": len(accounts), "people": len(people), "drafts": sum(bool(p["body"]) for p in people),
                       "approved": sum(p["draft_status"] == "approved" for p in people), "verified_emails": sum(p["email_status"] == "verified" for p in people),
                       "sent": 0},
            "outagehub_clusters": __import__("outagehub").cluster_accounts([load(f) for f in path.glob("accounts/*/research.json")]) if plan.get("engine") == "outagehub_api" else [],
            "discovery_summary": load(path / "discovery" / "summary.json"),
            "outagehub_playbook": load(path / "sales-playbook.json") if plan.get("engine") == "outagehub_api" else None,
            "limitations": load(path / "limitations.json", [])}


def merge_queue_view(person, queued):
    """Keep local copy separate from the exact persisted execution snapshot."""
    current_blockers = list(person.get('blockers', []))
    differs = queued['touch_number'] == 1 and (
        person.get('subject', '') != queued.get('subject', '') or
        person.get('body', '') != queued.get('body', ''))
    for key in ('approval_hash', 'sender_mailbox', 'labels', 'attachment_filenames', 'blockers'):
        person[key] = queued[key]
    person['schedule'].update(recommended_send_utc=queued['send_at'],
        status='gmail_scheduled' if queued['status'] == 'gmail_scheduled' else 'recommended_only')
    if queued['touch_number'] == 1:
        person['draft_status'] = 'draft_ready' if queued['status'] == 'review' else queued['status']
    if differs:
        person['scheduled_version'] = {key: queued.get(key) for key in
            ('id', 'status', 'subject', 'body', 'send_at', 'approval_hash')}
        person['has_local_revision'] = True
        person['draft_status'] = 'held' if queued['status'] == 'held' else 'local_revision'
        person['approval_hash'] = None
        person['schedule']['status'] = person['draft_status']
        notice = ('Local revision only. Gmail still contains the earlier scheduled version.'
                  if queued['status'] == 'gmail_scheduled' else
                  'Local revision differs from the stored queue. Reconcile before approval.')
        person['blockers'] = [{'code': 'local_revision', 'label': notice}, *current_blockers]
    if person.get('contact_error'):
        person['approval_hash'] = None
        person['blockers'] = [{'code':'contact_identity','label':person['contact_error']}, *person['blockers']]


def review_catalog(root=WORKSPACE):
    result = []
    for path in sorted((root / "campaigns").glob("*")):
        if (path / "campaign.json").exists() and ((path / "mission.json").exists() or (path / "accounts").exists()):
            if not load(path / "mission.json",{}).get("reference_only"):
                result.append(review_campaign(path))
    from state import connect, projection
    with connect(root / ".runtime/outbound.sqlite3") as db:
        from daily_calendar import projection as calendar_projection
        calendar = calendar_projection(db, {c["id"] for c in result})
        operations = projection(db)
        from manual_sent import receipts
        manual_receipts = receipts(db)
        from pilot_loi import project as pilot_projection,metrics as pilot_metrics,STAGES as pilot_stages
        pilot_cases=pilot_projection(db)
    for c in result:
        for a in c["accounts"]:
            a['pilot_opportunity']=next((p for p in pilot_cases if p['campaign']==c['id'] and p['account_id']==a['id']),a.get('pilot_opportunity'))
            for p in a["contacts"]:
                p["sender_mailbox"] = __import__("execution").mailbox_policy(c["engine"]).get("sender_mailbox")
                p["attachment_filenames"] = [item["filename"] for item in p["readiness_context"].get("attachments", []) if item.get("filename")]
                st = next((x for x in operations["contacts"] if x["id"]=="/".join((c["id"],a["id"],p["id"]))), None)
                queued=next((x for x in operations["queue"] if x["contact_id"]=="/".join((c["id"],a["id"],p["id"]))),None)
                if queued:
                    merge_queue_view(p, queued)
                p["sent_messages"] = [e for e in calendar["entries"] if e["kind"]=="sent" and e["contact_id"]=="/".join((c["id"],a["id"],p["id"]))]
                for e in calendar["entries"]:
                    if e["contact_id"]=="/".join((c["id"],a["id"],p["id"])):
                        e["company"]=a.get("name") or e["company"]
                        e["timezone_source"]=p.get("schedule",{}).get("timezone_source") or e.get("timezone_source")
                if st:
                    p["state"] = st; p["outcome"] = {"type":st["reply_type"] or ("no_visible_reply" if st["touch_number"] else "not_sent")}
                    if st['touch_number'] and not (queued and queued['touch_number']==1):
                        p['draft_status']='sent'
                reported = next((r for r in manual_receipts if r['contact_id']=='/'.join((c['id'],a['id'],p['id'])) and r['draft_hash']==draft_hash(p['subject'],p['body'])),None)
                if reported:
                    p['sent_record'] = reported
                    p['draft_status'] = 'sent'
                    p['approval_hash'] = None
            a['contacted'] = any(p.get('state',{}).get('touch_number',0) for p in a['contacts'])
            a['first_contacted_at'] = min((p['state']['first_sent_at'] for p in a['contacts'] if p.get('state',{}).get('first_sent_at')),default=None)
        c["counts"]["sent"] = sum(p.get("state",{}).get("touch_number",0) for a in c["accounts"] for p in a["contacts"])
    from signals import projection as signal_projection
    with connect(root / ".runtime/outbound.sqlite3") as db: signals=signal_projection(db)
    from scoring import POLICIES
    business={"technical_contract":{},"wapahki_facility":{},"outagehub_api":{}}
    from decimal import Decimal
    for c in result:
        for a in c["accounts"]:
            op=a.get("opportunity")
            if not op: continue
            engine=c["engine"]
            if engine=="technical_contract":
                currency=op.get("currency")
                if currency and op["status"] in {"signed","paid","delivering","complete"}:
                    totals=business[engine].setdefault(currency,{"signed":0,"collected":0})
                    totals["signed"]+=float(Decimal(str(op["fee"])))
                    totals["collected"]+=sum(float(Decimal(str(p["amount"]))) for p in op.get("payments",[]) if p.get("status")=="funded" and p.get("currency")==currency)
            elif engine=="outagehub_api" and op["status"]=="customer":
                currency=op["currency"]; totals=business[engine].setdefault(currency,{"mrr":0,"arr":0})
                totals["mrr"]+=float(Decimal(str(op["mrr"])));totals["arr"]=totals["mrr"]*12
            elif engine=="wapahki_facility":business[engine][op["status"]]=business[engine].get(op["status"],0)+1
    return {"pilot_metrics": pilot_metrics(pilot_cases), "pilot_stages": pilot_stages, "gmail_shortcuts": [dict(link,engine=engine) for engine in ("technical_contract","wapahki_facility","outagehub_api") for mailbox in [__import__("execution").mailbox_policy(engine).get("sender_mailbox")] if mailbox for link in __import__("gmail_labels").shortcuts(mailbox)], "business":business, "signals":signals, "campaigns": result, "operations": operations, "calendar": calendar, "policies": POLICIES, "generated_at": datetime.now(timezone.utc).isoformat(), "sending_enabled": False}


def next_actions(path):
    data = review_campaign(path); plan = data["mission"]; tasks = []
    qualified = sum(a["qualification"]["verdict"] == "yes" for a in data["accounts"])
    target = plan.get("target_accounts", len(data["accounts"]))
    progress = len(data['accounts']) if data['engine'] == 'outagehub_api' and plan.get('screen_target_accounts') else qualified
    target = plan.get('screen_target_accounts', target) if data['engine'] == 'outagehub_api' else target
    if progress < target:
        if data['engine'] != 'wapahki_facility':
            tasks.append({"step": "discover_accounts", "remaining": target-progress, "instruction": "Research and source organizations at the requested screening or qualification level; do not fabricate rows to hit a count"})
        elif not data['accounts']:
            tasks.append({'step':'discover_deployed_cells', 'instruction':'Research specific operating cells and recoveries; no minimum send count.'})
    for account in data["accounts"]:
        if data['engine'] == 'wapahki_facility' and (account.get('cell_qualification') or {}).get('status') != 'QUALIFIED':
            if (account.get('cell_qualification') or {}).get('status') != 'HOLD':
                tasks.append({'step':'research_and_qualify_cell','account':account['id'],
                              'instruction':'Identify the operating cell, repeated human recovery, software mechanism, observable state and local owner. No email before QUALIFIED.'})
            continue
        if data['engine']=='wapahki_facility' and account.get('pilot_opportunity',{}):
            from pilot_loi import next_step
            pilot=account['pilot_opportunity']
            if pilot['stage'] not in {'research','contacted','closed'}:
                tasks.append({**next_step(pilot),'account':account['id']})
        if data["engine"] == "wapahki_facility" and not account.get("benchmark_hypothesis"):
            tasks.append({"step": "research_recovery_benchmark", "account": account["id"], "instruction": "Research plant objective, intervention surface, proposed baseline and guardrails; keep unknown new-vertical metrics unresolved"})
        if data["engine"] == "wapahki_facility" and not account.get("pilot_value_case"):
            tasks.append({"step": "research_customer_value", "account": account["id"], "instruction": "Connect the actual process to a plausible operational loss and customer benefit; distinguish confirmed KPIs from candidates"})
        if account["qualification"]["verdict"] != "yes":
            continue
        if len(account["contacts"]) < plan.get("people_per_account", 3):
            tasks.append({"step": "discover_and_rank_people", "account": account["id"]})
        for person in account["contacts"]:
            for step, needed in (("enrich_selected_contacts", person["email_status"] != "verified"),
                                 ("draft_and_rank_subject_body", not (path / "accounts" / account["id"] / person["id"] / "subject-body-ranking.json").exists()),
                                 ("recommend_local_send_time", not person["schedule"].get("timezone"))):
                if needed: tasks.append({"step": step, "account": account["id"], "person": person["id"]})
    if plan.get("engine")=="technical_contract" and target>=30:
        from state import connect
        with connect() as db:
            rows=[dict(r) for r in db.execute("SELECT * FROM contacts WHERE campaign=?",(path.name,))]
        sent=[r["first_sent_at"] for r in rows if r.get("first_sent_at")]
        serious=len({r["account_id"] for r in rows if r.get("reply_type") in {"positive","meeting_proposed","meeting_confirmed","next_step"}})
        if sent and (datetime.now(timezone.utc)-datetime.fromisoformat(min(sent))).days>=5 and serious<3 and not (path/"wave-2.json").exists():
            tasks.append({"step":"prepare_wave_2","accounts":30,"reason":"Five days after first contact, fewer than three serious conversations; prepare the next qualified wave within mission scope and record wave-2.json to avoid duplicates"})
    return {"tasks": tasks, "ready_for_review": data["counts"]["drafts"], "mode": "draft_only", "limitations": data["limitations"]}


def save_review(path, account_id, person_id, change):
    folder = path / "accounts" / slug(account_id) / slug(person_id)
    if change.get('status') in {'draft_ready', 'approved'}:
        brief = load(folder.parent / 'research.json', {})
        if brief.get('engine') == 'wapahki_facility':
            from research import writer_packet
            writer_packet(brief, read_sources(path), person_id)
    draft = selected_draft(folder)
    if not draft:
        raise ValueError("Review requires a generated draft")
    fingerprint = draft_hash(draft.get("subject", ""), draft["body"])
    if change.get("base_hash") != fingerprint:
        raise ValueError("Draft changed during review; refresh before saving")
    if change.get("status") not in {"draft_ready", "approved", "skipped", "held"}:
        raise ValueError("Review can save or approve content; it cannot send or schedule")
    if not all(isinstance(change.get(k), str) and change[k].strip() for k in ("subject", "body")) or "\n" in change["subject"] or "\r" in change["subject"]:
        raise ValueError("Subject and body are required")
    if change["status"]=="approved":
        from readiness import blockers
        account=next(a for a in review_campaign(path)["accounts"] if a["id"]==account_id)
        person=next(p for p in account["contacts"] if p["id"]==person_id)
        issues=blockers(person["readiness_context"],change["subject"],change["body"])
        if issues: raise ValueError('; '.join(x['label'] for x in issues))
        from state import connect,eligible,get,review_action
        with connect() as db:
            ok,why=eligible(db,get(db,'/'.join((path.name,account_id,person_id))),datetime.now(timezone.utc))
            if not ok: raise ValueError(why)
            row=db.execute("SELECT id,subject,body FROM scheduled_sends WHERE contact_id=? AND touch_number=1 AND status IN ('review','approved')",('/'.join((path.name,account_id,person_id)),)).fetchone()
            if not row or row['subject']!=change['subject'] or row['body']!=change['body']:
                raise ValueError('Save edits and prepare the exact queue item before approving')
            review_action(db,row['id'],'approved',change.get('approval_hash'))
    value = {k:change[k] for k in ("subject", "body", "status", "base_hash")}
    value.update(updated_at=datetime.now(timezone.utc).isoformat(), send_authorized=False, schedule_authorized=change['status']=='approved')
    write_json(folder / "review.json", value)
    from state import connect, event
    with connect() as db:
        cid="/".join((path.name,slug(account_id),slug(person_id)))
        event(db,cid,"draft_review",value["status"]+" · "+value["updated_at"])
        row=db.execute("SELECT * FROM contacts WHERE id=?",(cid,)).fetchone()
        if row and row["touch_number"]==0:
            context=json.loads(row["context"]);context.update(subject=value["subject"],body=value["body"],draft_hold=value['status']=='held')
            if value["status"]=="skipped":context["qualified"]=False
            db.execute("UPDATE contacts SET context=?,draft_version=?,original_subject=? WHERE id=?",(json.dumps(context),draft_hash(value["subject"],value["body"]),value["subject"],cid))
            status={"approved":"approved","skipped":"skipped","draft_ready":"review","held":"held"}[value["status"]]
            db.execute("UPDATE scheduled_sends SET subject=?,body=?,status=?,reviewed_at=? WHERE contact_id=? AND touch_number=1 AND status IN ('review','approved','needs_draft','held')",(value["subject"],value["body"],status,value["updated_at"] if status=="approved" else None,cid))
    return value


def mark_sent(path, account_id, person_id, value):
    from state import connect, get
    from manual_sent import record
    cid='/'.join((path.name,account_id,person_id))
    data=review_campaign(path)
    account=next(a for a in data['accounts'] if a['id']==account_id)
    person=next(p for p in account['contacts'] if p['id']==person_id)
    with connect() as db:
        c=get(db,cid)
        subject,body=person['subject'],person['body'];touch=1
        if value.get('action_id') is not None:
            q=db.execute('SELECT * FROM scheduled_sends WHERE id=? AND contact_id=?',(value['action_id'],cid)).fetchone()
            if not q: raise ValueError('Queued email no longer exists')
            subject,body,touch=q['subject'],q['body'],q['touch_number']
        if value.get('draft_hash') != draft_hash(subject,body):
            raise ValueError('The displayed email changed. Refresh before marking it sent.')
        return record(db,cid,subject,body,c['sender_mailbox'],person['email'],value['sent_at'],value['request_id'],touch)


if __name__ == "__main__":
    try:
        args = sys.argv[1:]
        if args == ["review-catalog"]:
            result = review_catalog()
        elif args == ["create-mission"]:
            value=json.load(sys.stdin)
            engine=value.get("engine")
            overrides={"engine":engine,"project":{"technical_contract":"personal technical work","wapahki_facility":"Wapahki","outagehub_api":"OutageHub"}[engine]} if engine in {"technical_contract","wapahki_facility","outagehub_api"} else None
            result=create_mission(value.get("goal"),overrides=overrides)
        elif args == ["calendar-action"]:
            from state import connect
            from daily_calendar import change_plan
            with connect() as db: result=change_plan(db,json.load(sys.stdin))
        elif args == ["review-action"]:
            from state import connect,review_action
            value=json.load(sys.stdin)
            with connect() as db: result=review_action(db,int(value["id"]),value["status"],value.get('approval_hash'))
        elif len(args) == 4 and args[0] == "save-review":
            result = save_review(campaign(args[1]), args[2], args[3], json.load(sys.stdin))
        elif len(args) == 4 and args[0] == "mark-sent":
            result = mark_sent(campaign(args[1]), args[2], args[3], json.load(sys.stdin))
        else:
            raise ValueError("Unsupported local review operation")
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)})); sys.exit(2)
