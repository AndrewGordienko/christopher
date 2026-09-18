"""Validate proposed recovery evaluations; never manufacture results or access."""
import re

EVENT_MODEL_VERSION = "recovery-v1"
AUTONOMY_METRICS = {"autonomous_recovery_rate", "autonomous_recovery_percent"}


def recipient_altitude(role, selected=None):
    """Role prior; a caller still resolves unusual/remit-specific cases explicitly."""
    title = role.casefold()
    if re.search(r"vice.?pr[eé]sident|\bvp\b|\bchief\b|\bcoo\b|\bcto\b|\bceo\b|\bpresident\b|founder|corporate director|national director|deputy director general", title):
        return "corporate_technical"
    if re.search(r"engineering|ing[eé]nierie|ing[eé]nieur|maintenance|automation|controls|electrical|technical director|laboratoire|réingénierie", title):
        return "automation_controls"
    if re.search(r"plant|usine|production|operations|opérations|general manager|directeur g[eé]n[eé]ral", title):
        return "plant_operations"
    if selected in {"automation_controls", "plant_operations", "corporate_technical"}:
        return selected
    return "routing"


def recipient_strategy(role):
    function = recipient_altitude(role)
    return {"function": function, "question_focus": {
        "automation_controls": "Offer to connect available alarms/machine states with interventions, identify recurring recovery sequences and evaluate technically recoverable cases.",
        "plant_operations": "Offer to quantify productive time lost to interventions and test recovery software against the facility's output and quality guardrails.",
        "corporate_technical": "Offer a measurable result at one scoped facility, then test whether the approach transfers across operations.",
        "routing": "Establish who owns automation and recovery at this facility; do not assume the recipient owns the line."
    }[function], "first_touch": "Connect Wapahki's recovery software to a sourced process, a conditional operational loss and a concrete baseline/recovery-evaluation offer. Ask whether the problem merits a short remote technical call. Existing data can explain the mechanism; do not request its delivery, control, an LOI or formal commitment cold. Never claim unknown logging, losses or savings. Resolve unconfirmed site remit. No visit CTA while Andrew is in London, UK."}


def validate_benchmark(value, facts, facility_id):
    if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("status") != "proposed":
        raise ValueError("Benchmark hypothesis must be a versioned proposal, not a result")

    def refs(ids, facility=False):
        if not ids or any(i not in facts for i in ids):
            raise ValueError("Benchmark evidence requires known fact IDs")
        if facility and any(facts[i]["entity_id"] != facility_id for i in ids):
            raise ValueError("A confirmed plant measure needs evidence for this facility")

    refs(value.get("basis"))
    if value.get("mode") not in {"pilot", "discovery"} or not value.get("vertical"):
        raise ValueError("Resolve Wapahki pilot versus new-vertical discovery mode")
    if value.get("adapter_status") not in {"hypothesis", "pilot_ready"} or not value.get("adapter_id"):
        raise ValueError("Benchmark requires an identified adapter and its evidence status")
    obj = value.get("existing_production_objective", {})
    if obj.get("status") not in {"confirmed", "unconfirmed"}:
        raise ValueError("Preserve whether the plant KPI is actually confirmed")
    for item in obj.get("public_measures", []):
        if item.get("kind") not in {"design_capacity", "target", "reported_performance", "permit_limit", "process_quality", "investment", "access_signal", "unknown"} or not item.get("description"):
            raise ValueError("Classify public measures without turning capacity into performance")
        refs(item.get("basis"))
    if obj["status"] == "confirmed" and not obj.get("confirmed_kpis"):
        raise ValueError("Confirmed plant KPIs need specific supporting facts")
    for item in obj.get("confirmed_kpis", []):
        if not item.get("metric"): raise ValueError("Name the confirmed plant KPI")
        refs(item.get("basis"), facility=True)
    unit = value.get("production_unit", {})
    if unit.get("status") not in {"proposed", "confirmed", "unknown"} or not unit.get("definition"):
        raise ValueError("Define the production denominator or its unresolved question")
    if unit.get("status") == "confirmed": refs(unit.get("basis"), facility=True)
    primary = value.get("primary_wapahki_metric", {})
    if primary.get("phase") != "observational_baseline" or primary.get("id") in AUTONOMY_METRICS:
        raise ValueError("An observational baseline cannot measure autonomous recovery efficacy")
    if primary.get("status") not in {"proposed", "unknown"} or not primary.get("definition"):
        raise ValueError("Define the proposed intervention measure without inventing a result")
    if value["mode"] == "pilot" and (not unit.get("type") or not primary.get("id") or not value.get("task_success")):
        raise ValueError("Pilot mode needs a proposed unit, recovery measure and task success predicate")
    for metric in value.get("secondary", []):
        if metric.get("phase") not in {"observational_baseline", "authorized_intervention"}:
            raise ValueError("Separate baseline metrics from later intervention metrics")
        if metric.get("id") in AUTONOMY_METRICS and metric["phase"] != "authorized_intervention":
            raise ValueError("Autonomous recovery requires a later authorized intervention phase")
    if not value.get("plant_guardrails"):
        raise ValueError("A recovery benchmark needs underlying task and safety guardrails")
    for item in value["plant_guardrails"]:
        if item.get("status") not in {"proposed", "confirmed"} or not item.get("metric"):
            raise ValueError("Preserve proposed versus confirmed guardrails")
        refs(item.get("basis"), facility=item["status"] == "confirmed")
    for item in value.get("likely_failure_classes", []):
        if item.get("status") not in {"hypothesis", "documented"} or not item.get("class"):
            raise ValueError("Preserve failure hypothesis versus documented event")
        refs(item.get("basis"), facility=item["status"] == "documented")
    baseline = value.get("baseline_plan", {})
    if baseline.get("event_model_version") != EVENT_MODEL_VERSION:
        raise ValueError("Use the shared versioned recovery event model")
    for key in ("exposure_definition", "intervention_definition", "downtime_definition", "stability_criterion", "comparison_plan", "unknowns"):
        if not baseline.get(key): raise ValueError("Benchmark baseline needs " + key)
    if not value.get("data_sources") or not value.get("outreach_question"):
        raise ValueError("Connect the measurement proposal to observable data and a conversation")
    readiness = value.get("readiness", {})
    if not readiness or not readiness.get("status"):
        raise ValueError("Keep access and baseline readiness explicit")
    for key in ("data_access_confirmed", "baseline_measured", "control_authorized"):
        if type(readiness.get(key)) is not bool:
            raise ValueError("Benchmark readiness requires explicit " + key)
        if readiness[key]: refs(readiness.get(key + "_basis"), facility=True)
    if value["adapter_status"] == "pilot_ready" or (value["mode"] == "pilot" and value["vertical"] != "recycling"):
        promotion = value.get("promotion", {})
        observations = promotion.get("observations", [])
        if len({o.get("observation_id") for o in observations if o.get("observation_id")}) < 3:
            raise ValueError("Vertical promotion needs several independent sourced observations")
        if len({o.get("company_id") for o in observations if o.get("company_id")}) < 3:
            raise ValueError("Vertical promotion requires the pattern at three distinct companies")
        for observation in observations:
            if observation.get("kind") not in {"conversation", "site_observation", "telemetry_review"} or not observation.get("facility_id"):
                raise ValueError("Public marketing research is not a discovery observation")
            refs(observation.get("basis"))
        if not all(promotion.get(k) is True for k in ("consistent_pattern", "adapter_complete", "contradictions_resolved")) or not promotion.get("reason"):
            raise ValueError("Conversation count alone cannot establish a reusable pilot adapter")
        for key in ("pain_owner", "buyer", "telemetry", "failure_taxonomy", "success_metric", "denominator", "safe_recovery_actions", "pilot_scope"):
            answer = promotion.get("answers", {}).get(key, {})
            if not answer.get("answer"):
                raise ValueError("Vertical promotion must resolve " + key)
            refs(answer.get("basis"))
    return value


def writer_context(value):
    """The writer gets the operational question, not the metric framework."""
    return {"mode": value["mode"], "status": value["status"],
            "operational_question": value["outreach_question"],
            "primary_measure": value["primary_wapahki_metric"].get("id"),
            "plant_kpi_status": value["existing_production_objective"]["status"],
            "instruction": "Personalize the operational value case: propose quantifying costly interventions using relevant existing records when available and agreed, then testing recovery software against those cases. Keep unknown losses, KPIs and data availability conditional. Ask whether the issue warrants a remote call, not a research interview or visit. No raw-data delivery, LOI or control ask; no guaranteed savings."}


def validate_value_case(value, facts, facility_id):
    if not isinstance(value, dict) or value.get("status") != "hypothesis":
        raise ValueError("A pilot value case is a customer-value hypothesis, not a savings claim")
    for field in ("basis",):
        if not value.get(field) or not set(value[field]) <= set(facts):
            raise ValueError("Customer value must trace to the researched process")
    business = value.get("business_metric", {})
    if business.get("status") not in {"confirmed", "unconfirmed"}:
        raise ValueError("Keep the customer's actual KPI distinct from a candidate")
    if business["status"] == "unconfirmed" and business.get("primary") is not None:
        raise ValueError("An unconfirmed business metric must remain a candidate")
    if business["status"] == "confirmed":
        ids = business.get("evidence", [])
        if not business.get("primary") or not ids or any(i not in facts or facts[i]["entity_id"] != facility_id for i in ids):
            raise ValueError("Confirmed customer KPI needs evidence for this plant")
    link = value.get("economic_link", {})
    if link.get("hypothesis") is not True or len(link.get("chain", [])) < 4 or not link.get("basis") or not set(link["basis"]) <= set(facts):
        raise ValueError("Establish a conditional process-to-customer-value chain before writing")
    for key in ("automation", "failure_hypotheses", "wapahki_metric", "pilot_value_proposition", "first_step", "value_exchange", "geography", "data_rights"):
        if not value.get(key): raise ValueError("Pilot value case needs " + key)
    return value
