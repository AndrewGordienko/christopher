"""Campaign persistence and evidence boundary between research and writing."""
from pathlib import Path
from datetime import datetime, timezone
import json
import re

WORKSPACE = Path(__file__).resolve().parents[3]
STAGES = {"research_visit", "workflow_conversation", "design_partner", "pilot", "proposal", "technical_contract", "reply", "schedule", "investor", "acquisition", "api_sales", "customer", "personal_reply"}


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not value:
        raise ValueError("A nonempty campaign/account name is required")
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def campaign(name, goal=None, root=WORKSPACE):
    path = root / "campaigns" / slug(name)
    if goal is not None:
        if not (path / "campaign.json").exists():
            write_json(path / "campaign.json", {"name": name, "goal": goal, "mode": "draft_only", "created_at": datetime.now(timezone.utc).isoformat()})
            (path / "campaign.md").write_text(f"# {name}\n\n{goal}\n\nStatus: research pending.\n")
    return path


def read_sources(path):
    file = path / "sources.jsonl"
    # JSONL records end at LF. Unicode line separators can legally occur inside
    # a JSON string and must stay in the captured source text.
    return {s["id"]: s for s in (json.loads(line) for line in file.read_text().split("\n") if line.strip())} if file.exists() else {}


def add_source(path, source):
    for key in ("id", "url", "observed_at", "tool", "tool_ref", "text"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"Source needs {key} from an actual tool result")
    datetime.fromisoformat(source["observed_at"].replace("Z", "+00:00"))
    if not source["url"].startswith(("https://", "http://", "gmail:", "user:")):
        raise ValueError("Source must identify the viewed public page or Gmail message")
    known = read_sources(path)
    if source["id"] in known:
        if known[source["id"]] != source:
            raise ValueError("Source IDs are immutable; a refreshed page needs a new ID")
        return
    path.mkdir(parents=True, exist_ok=True)
    with (path / "sources.jsonl").open("a") as f:
        f.write(json.dumps(source, ensure_ascii=False) + "\n")


def validate_brief(brief, sources):
    for key in ("company", "facts", "hypotheses", "stakeholders", "qualification", "recommended_motion", "message_strategy"):
        if key not in brief:
            raise ValueError(f"AccountBrief missing {key}")
    if not brief["company"].get("name") or not brief["company"].get("id"):
        raise ValueError("Resolve the company identity first")
    facts = {}
    for fact in brief["facts"]:
        if not fact.get("id") or fact["id"] in facts or not fact.get("text") or not fact.get("entity_id"):
            raise ValueError("Facts need unique IDs, entity_id and text")
        if not fact.get("evidence"):
            raise ValueError("Every fact needs captured source evidence")
        for e in fact["evidence"]:
            source = sources.get(e.get("source_id"))
            if not source or not e.get("quote") or e["quote"] not in source["text"]:
                raise ValueError("Fact quote must occur in an actual captured source")
        facts[fact["id"]] = fact

    def refs(ids, reason, required=True):
        if (required and not ids) or any(i not in facts for i in ids):
            raise ValueError(f"{reason} needs known fact IDs")

    refs(brief["company"].get("fact_ids", []), "Company identity")
    for h in brief["hypotheses"]:
        refs(h.get("basis", []), "Hypothesis")
        if not h.get("statement") or h.get("confidence") not in {"low", "medium", "high"}:
            raise ValueError("Hypothesis requires statement and confidence")
    ids = set(); ranks = set()
    for person in brief["stakeholders"]:
        if not person.get("id") or person["id"] in ids or not person.get("name") or not person.get("role"):
            raise ValueError("Stakeholders need unique IDs, actual names and sourced roles")
        ids.add(person["id"])
        if person.get("rank") in ranks: raise ValueError("Stakeholder ranks must be unique")
        ranks.add(person.get("rank"))
        refs(person.get("fact_ids", []), "Contact identity/role")
        if person.get("email"):
            refs(person.get("email_fact_ids", []), "Contact address")
        if person.get("rank") not in (1, 2, 3) or not person.get("reason"):
            raise ValueError("Rank up to three stakeholders and explain ownership")
    q = brief["qualification"]
    if q.get("verdict") not in {"yes", "maybe", "no"} or not q.get("reason"):
        raise ValueError("Qualification requires yes/maybe/no and rationale")
    if "score" in q and (type(q["score"]) not in (int, float) or not 0 <= q["score"] <= 100):
        raise ValueError("Fit score must be a 0–100 research judgment, not a probability")
    refs(q.get("basis", []), "Qualification", required=q["verdict"] == "yes")
    engine = brief.get("engine")
    if engine == "wapahki_facility":
        facility = brief.get("facility", {})
        if not facility.get("id") or not facility.get("name") or not facility.get("location"):
            raise ValueError("Wapahki qualifies a specific facility, not just its parent company")
        if facility.get("subvertical") not in {"material_recovery", "tire_recycling", "tire_retreading", "other_automation"}:
            raise ValueError("Resolve the facility sub-vertical")
        refs(facility.get("fact_ids", []), "Facility identity/location")
        if any(facts[f]["entity_id"]!=facility["id"] for f in facility["fact_ids"]):
            raise ValueError("Parent-company evidence cannot establish a particular facility")
        for process in facility.get("automation", []):
            refs(process.get("fact_ids", []), "Facility automation")
            if any(facts[f]["entity_id"]!=facility["id"] for f in process["fact_ids"]):
                raise ValueError("Automation evidence must belong to this facility")
        if q["verdict"] == "yes" and not facility.get("automation"):
            raise ValueError("Qualified facilities need sourced equipment evidence")
        if brief.get('cell_qualification') is not None:
            from cell_qualification import validate as validate_cell
            cell = validate_cell(brief['cell_qualification'], facts, facility['id'])
            owner = cell['criteria']['technical_owner'].get('person_id')
            if owner and owner not in ids:
                raise ValueError('Cell technical owner must be a researched stakeholder')
        if brief.get("benchmark_hypothesis") is not None:
            from benchmarks import validate_benchmark
            validate_benchmark(brief["benchmark_hypothesis"], facts, facility["id"])
        if brief.get("pilot_value_case") is not None:
            from benchmarks import validate_value_case
            validate_value_case(brief["pilot_value_case"], facts, facility["id"])
    if engine == "outagehub_api" and q["verdict"] == "yes":
        gap = brief.get("grid_data_gap", {})
        for key in ("existing_product", "current_observability", "event_changes_workflow", "incremental_information", "buyer_function"):
            if not gap.get(key): raise ValueError("OutageHub needs " + key + " before outreach")
        refs(gap.get("basis", []), "External grid-data gap")
        discovery = brief.get("qualification_scope") == "workflow_discovery"
        if discovery or brief.get("outagehub_integration"):
            from outagehub import validate_integration, score_integration
            validate_integration(brief, facts)
            if brief.get("outagehub_score"):
                expected = score_integration(brief["outagehub_score"]["assessments"], facts)
                if expected != brief["outagehub_score"]:
                    raise ValueError("OutageHub score does not match its evidence-backed assessments")
        if not discovery and gap.get("equivalent_internal_visibility") is not False:
            raise ValueError("Resolve equivalent internal grid visibility before qualifying; telemetry alone is not disqualifying")
        competition = brief.get("competitive_check", {})
        if not competition.get("checked_at") or not competition.get("alternatives") or not competition.get("credible_difference"):
            raise ValueError("OutageHub needs a current alternatives check and supported reason to compete")
        checked = datetime.fromisoformat(competition["checked_at"].replace("Z", "+00:00"))
        if checked.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-checked).days <= 30:
            raise ValueError("Refresh the competitive check within 30 days")
        refs(competition.get("basis", []), "Competitive comparison")
        refs(competition.get("product_fact_ids", []), "Current OutageHub capabilities")
    motion = brief["recommended_motion"]
    if motion.get("stage") not in STAGES or not motion.get("ask"):
        raise ValueError("Resolve the actual stage and first ask")
    refs(motion.get("interest_basis", []), "Existing interest", required=motion["stage"] in {"design_partner", "pilot", "proposal"})
    strategy = brief["message_strategy"]
    expose = strategy.get("expose_facts", [])
    if len(expose) > 2:
        raise ValueError("Writer receives at most two selected research facts")
    refs(expose, "Writer facts", required=False)
    refs(strategy.get("why_now_basis", []), "Why now", required=bool(strategy.get("why_now")))
    motivation = strategy.get("motivation")
    if motivation is not None:
        if not isinstance(motivation, dict) or motivation.get("kind") != "inference":
            raise ValueError("Impact motivation is an inference, not a sourced company fact")
        for key in ("societal_outcome", "technical_problem", "andrew_connection"):
            if not isinstance(motivation.get(key), str) or not motivation[key].strip():
                raise ValueError("Impact motivation needs " + key)
        refs(motivation.get("basis", []), "Impact motivation")
    if not strategy.get("central_reason") or not strategy.get("problem_altitude"):
        raise ValueError("Choose one central reason and the recipient's problem level")
    return facts


def save_account(path, brief):
    sources = read_sources(path)
    validate_brief(brief, sources)
    target = path / "accounts" / slug(brief.get("facility", brief["company"])["id"])
    write_json(target / "research.json", brief)
    write_json(target / "contacts.json", brief["stakeholders"])
    (target / "sources.md").write_text("# Sources\n\n" + "\n".join(f"- [{s['id']}]({s['url']}) · observed {s['observed_at']}" for s in sources.values()) + "\n")
    s = brief["message_strategy"]; m = brief["recommended_motion"]
    (target / "strategy.md").write_text(f"# {brief['company']['name']}\n\n{brief['qualification']['verdict'].upper()}: {brief['qualification']['reason']}\n\nReason for writing: {s['central_reason']}\n\nStage: {m['stage']}\n\nAsk: {m['ask']}\n")
    return target


def writer_packet(brief, sources, person_id):
    facts = validate_brief(brief, sources)
    if brief.get('engine') == 'wapahki_facility':
        from cell_qualification import context as cell_context, qualification_blockers
        issues = qualification_blockers(cell_context(brief))
        if issues:
            raise ValueError('; '.join(i['label'] for i in issues))
    if brief.get("engine") == "wapahki_facility" and not brief.get("benchmark_hypothesis"):
        raise ValueError("Research a benchmark hypothesis or discovery questions before new Wapahki drafting")
    if brief.get("engine") == "wapahki_facility" and not brief.get("pilot_value_case"):
        raise ValueError("Research a credible customer-value chain before Wapahki drafting")
    if brief["qualification"]["verdict"] != "yes":
        raise ValueError("Resolve a Maybe or No before automatic drafting")
    person = next((p for p in brief["stakeholders"] if p["id"] == person_id), None)
    if not person:
        raise ValueError("Writer recipient must be a researched stakeholder")
    s = brief["message_strategy"]
    return {"recipient": {k: person[k] for k in ("id", "name", "role", "seniority", "department", "email") if k in person},
            "company": {k: brief["company"][k] for k in ("id", "name", "industry", "facility") if k in brief["company"]},
            "central_reason": s["central_reason"], "problem_altitude": s["problem_altitude"],
            "cell_context": __import__('cell_qualification').context(brief) if brief.get('engine') == 'wapahki_facility' else None,
            "motivation": s.get("motivation"),
            "recipient_strategy": __import__("benchmarks").recipient_strategy(person["role"]) if brief.get("engine") == "wapahki_facility" else None,
            "benchmark_context": __import__("benchmarks").writer_context(brief["benchmark_hypothesis"]) if brief.get("benchmark_hypothesis") else None,
            "customer_value_context": {k: brief["pilot_value_case"][k] for k in ("pilot_value_proposition", "first_step")} if brief.get("pilot_value_case") else None,
            "commercial_context": {"eventual_goal":"One-cell recovery pilot with a qualified owner and authority path", "first_touch":"Specific cell, conditional recurring human-recovery mechanism, passive observation of faults/actions/restored state, then evaluate one suitable safe recovery if justified and separately authorized. Ask for a short technical conversation or the cell owner. No broad downtime consultancy or cold data/control/LOI request."} if brief.get("engine") == "wapahki_facility" else None,
            "objective": brief["recommended_motion"],
            "facts": [facts[i] for i in s.get("expose_facts", [])],
            "hypotheses": brief["hypotheses"][:1], "why_now": s.get("why_now"),
            "do_not_claim": s.get("do_not_claim", []) + ["An inferred recovery problem is not a known failure", "No old price, metric, availability or capability without current support"],
            "research_instruction": "This packet is the research boundary. Before composing, compress sender context and research through meaning, recipient relevance and the shortest natural phrase that preserves both, following references/human-compression.md. Keep original source evidence intact and retain scope, timing and uncertainty. Preserve the current task draft's useful meaning and Andrew's thought; use history to calibrate cadence. Do not browse while composing."}
