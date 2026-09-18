"""Source-backed ordinal fit assessments, explicitly not calibrated probabilities."""
from pathlib import Path
import json

POLICIES = json.loads((Path(__file__).resolve().parents[1] / "policies/motions.json").read_text())


def score_fit(assessments, fact_ids, engine="technical_contract", person=False):
    policy = POLICIES[engine]
    key = "person_weights" if person else ("facility_weights" if engine == "wapahki_facility" else "company_weights")
    weights = policy.get(key, POLICIES["technical_contract"]["person_weights"])
    score = coverage = 0
    for dimension, weight in weights.items():
        item = assessments.get(dimension)
        if not item or item.get("rating") is None:
            continue
        if type(item["rating"]) not in (int, float) or not 0 <= item["rating"] <= 5:
            raise ValueError("Fit dimensions use 0–5 ordinal judgments")
        if not item.get("reason") or not item.get("basis") or not set(item["basis"]) <= set(fact_ids):
            raise ValueError("Fit dimensions need a reason and captured fact IDs")
        score += weight * item["rating"] / 5
        coverage += weight
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"
    if engine == "wapahki_facility" and not person:
        # Legacy automation scores remain research data and cannot qualify outreach.
        grade = 'UNQUALIFIED'
    return {"score": round(score, 1), "grade": grade, "evidence_coverage": coverage,
            "interpretation": "Research judgment, not reply probability or proof of a budget/problem", "assessments": assessments}
