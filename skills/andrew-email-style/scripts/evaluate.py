"""Pinned write-like-me measurements plus an independent contextual critic contract."""
import sys
import json
from history import ROOT

sys.path.insert(0, str(ROOT / "third_party/write_like_me"))
from stylometry import compute_features
from voice_check import check_text


def features(body):
    return compute_features(body, use_textstat=False, use_spacy=False)


def rank(candidates, retrieval, critic, packet=None):
    if (packet or {}).get('benchmark_context') or (packet or {}).get('cell_context'):
        from cell_qualification import qualification_blockers
        issues = qualification_blockers((packet or {}).get('cell_context') or {})
        if issues:
            raise ValueError('; '.join(i['label'] for i in issues))
    profile = json.loads((ROOT / "references/voice-check.json").read_text())
    responses = {r["id"] for r in retrieval.get("response_examples", [])}
    fact_ids = {f["id"] for f in (packet or {}).get("facts", [])}
    task_draft = (packet or {}).get("task_draft") or retrieval.get("task_draft")
    rows = []; seen = set()
    for candidate in candidates:
        cid = candidate["id"]
        if cid in seen:
            raise ValueError("Candidate IDs must be unique")
        seen.add(cid)
        c = critic.get(cid, {})
        text = candidate.get("subject", "") + "\n\n" + candidate["body"]
        check = check_text(text, profile, "email", skip_citations=False)
        reasons = []
        if not candidate["body"].strip():
            reasons.append("empty email")
        for gate in ("facts_supported", "thought_preserved", "plain_language_preserved", "research_quiet", "stage_correct"):
            if c.get(gate) is not True:
                reasons.append(gate)
        if task_draft:
            for gate in ("task_draft_preserved", "technical_detail_preserved"):
                if c.get(gate) is not True:
                    reasons.append(gate)
        if (packet or {}).get("sender_context") or retrieval.get("sender_context"):
            if c.get("sender_context_fit") is not True:
                reasons.append("sender_context_fit")
        for score in ("voice_fit", "recipient_fit"):
            if isinstance(c.get(score), bool) or not isinstance(c.get(score), (int, float)) or not 0 <= c[score] <= 5:
                reasons.append(score)
        if c.get("ai_sentence") or c.get("reject"):
            reasons.append("critic rejected wording")
        if check["verdict"] == "BLOCK" or "—" in text:
            reasons.append("hard voice ban")
        if check["verdict"] == "REVIEW" and c.get("phrase_flags_reviewed") is not True:
            reasons.append("unreviewed phrase flag")
        if not set(c.get("response_evidence_ids", [])) <= responses:
            reasons.append("unknown response evidence")
        if packet is not None and not set(c.get("research_fact_ids", [])) <= fact_ids:
            reasons.append("research outside writer packet")
        # Response evidence only breaks near-ties after voice/context gates; no pseudo-probability.
        score = .7 * c.get("voice_fit", 0) + .3 * c.get("recipient_fit", 0) if not reasons else None
        rows.append({"id": cid, "eligible": not reasons, "rejection_reasons": reasons, "score": score,
                     "response_tiebreak": bool(c.get("response_evidence_ids")) and bool(c.get("response_reason")),
                     "voice_check": check, "stylometry": features(candidate["body"])})
    eligible = sorted([r for r in rows if r["eligible"]], key=lambda r: r["score"], reverse=True)
    winner = None
    if eligible:
        near = [r for r in eligible if eligible[0]["score"] - r["score"] <= .15]
        winner = max(near, key=lambda r: (r["response_tiebreak"], r["score"]))["id"]
    return {"winner": winner, "candidates": rows, "response_probability": None,
            "limitations": "Stylometry is diagnostic. Source-ID validation checks traceability; Codex critic checks meaning. No trained response model."}
