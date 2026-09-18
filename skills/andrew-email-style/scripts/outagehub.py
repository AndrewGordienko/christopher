"""Evidence-backed OutageHub workflow qualification and ordinal ranking."""
from collections import defaultdict

WEIGHTS = {
    "integration_fit": 15, "existing_workflow": 20, "economic_pain": 10,
    "canadian_exposure": 15, "ability_to_buy": 5, "ease_of_integration": 10,
    "distribution_leverage": 25,
}


def validate_integration(brief, facts):
    profile = brief.get("outagehub_integration") or {}
    for key in ("relevant_product", "existing_workflow", "insertion_point", "beneficiary",
                "customer_benefit", "canadian_relevance", "buy_vs_build", "buyer_function",
                "integration_sentence", "use_case_cluster", "next_question"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError("OutageHub workflow research needs " + key)
    if profile.get("product") not in {"API", "Notifications", "Historical"}:
        raise ValueError("Select API, Notifications or Historical")
    if not profile.get("basis") or not set(profile["basis"]) <= set(facts):
        raise ValueError("Integration must cite current workflow evidence")
    gap = brief.get("grid_data_gap", {})
    if gap.get("equivalent_internal_visibility") not in (None, False, True):
        raise ValueError("Internal outage visibility must be true, false or unknown")
    if gap.get("equivalent_internal_visibility") is True and not profile.get("supported_incremental_difference"):
        raise ValueError("Known equivalent coverage requires an evidenced incremental difference")
    if profile.get("supported_incremental_difference"):
        refs = profile.get("difference_basis", [])
        if not refs or not set(refs) <= set(facts):
            raise ValueError("Incremental difference needs fact IDs")
    if brief.get("qualification_scope") == "workflow_discovery":
        if brief["recommended_motion"].get("stage") != "workflow_conversation":
            raise ValueError("Workflow discovery cannot imply a verified data gap or evaluation")
        if profile.get("gap_status") not in {"unknown", "hypothesis", "partial_coverage"}:
            raise ValueError("Discovery must preserve the unconfirmed data gap")
    return profile


def score_integration(assessments, fact_ids):
    total = weighted = count = 0
    unknown = []
    for key, weight in WEIGHTS.items():
        item = assessments.get(key) or {}
        value = item.get("rating")
        if value is None:
            unknown.append(key)
            continue
        if type(value) not in (int, float) or not 0 <= value <= 5:
            raise ValueError("OutageHub scores must be 0–5 or null")
        if not item.get("reason") or not item.get("basis") or not set(item["basis"]) <= set(fact_ids):
            raise ValueError("OutageHub scores need reasoning and known fact IDs")
        total += value
        weighted += weight * value / 5
        count += 1
    return {"raw_total": total, "raw_max": 35, "weighted_priority": round(weighted, 1),
            "assessed_dimensions": count, "unknown_dimensions": unknown,
            "weights": WEIGHTS, "assessments": assessments,
            "interpretation": "Ordinal fit judgment. Unknown dimensions earn no points; not proof of budget, pain or buying intent."}


def cluster_accounts(briefs):
    groups = defaultdict(list)
    seen = set()
    for brief in briefs:
        profile = brief.get("outagehub_integration")
        if not profile or brief["qualification"]["verdict"] != "yes":
            continue
        company = brief["company"]
        buying_group = company.get("pause_group") or company.get("domain") or company["id"]
        if buying_group in seen:
            continue
        seen.add(buying_group)
        groups[profile["use_case_cluster"]].append({"id": company["id"], "name": company["name"],
            "integration": profile["integration_sentence"], "basis": profile["basis"],
            "priority": brief.get("outagehub_score", {}).get("weighted_priority"),
            "gap_status": profile.get("gap_status", "unknown")})
    return [{"use_case": key, "count": len(rows), "accounts": rows,
             "interpretation": "Repeated researched workflow fit; customer demand remains unconfirmed."}
            for key, rows in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))]
