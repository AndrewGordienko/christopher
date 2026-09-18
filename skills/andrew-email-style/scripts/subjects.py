"""Rank agent-generated subjects with Andrew history and the actual email body."""
import re
from evaluate import rank

BAD = re.compile(r"revolutioniz|unlock(?:ing)?|exciting collaboration opportunity|\bAI\s*[x×]\s*|\bAndrew\s*[x×]\s*", re.I)


def rank_subjects(candidates, retrieval, critic, is_reply=False):
    history_ids = {r["id"] for r in retrieval.get("voice_examples", []) + retrieval.get("recipient_history", [])}
    response_ids = {r["id"] for r in retrieval.get("response_examples", [])}
    seen = set(); rows = []
    for candidate in candidates:
        sid, subject = candidate["id"], candidate["subject"].strip()
        if sid in seen:
            raise ValueError("Subject IDs must be unique")
        seen.add(sid); c = critic.get(sid, {}); reasons = []
        for gate in ("facts_supported", "plain_language", "context_fit", "no_fake_personalization"):
            if c.get(gate) is not True:
                reasons.append(gate)
        if not subject or "\n" in subject or "\r" in subject or "—" in subject or BAD.search(subject):
            reasons.append("subject language")
        if not is_reply and re.match(r"^(re|fwd?)\s*:", subject, re.I):
            reasons.append("fake thread prefix")
        if subject.casefold() == "quick question" and not c.get("specific_reason_for_quick_question"):
            reasons.append("generic quick question")
        for key in ("voice_fit", "recipient_fit", "body_fit"):
            if type(c.get(key)) not in (int, float) or not 0 <= c[key] <= 5:
                reasons.append(key)
        if not set(c.get("history_ids", [])) <= history_ids or not set(c.get("response_ids", [])) <= response_ids:
            reasons.append("unretrieved subject evidence")
        if c.get("reject"):
            reasons.append("critic rejection")
        score = .4*c.get("voice_fit", 0)+.3*c.get("recipient_fit", 0)+.3*c.get("body_fit", 0) if not reasons else None
        rows.append({"id": sid, "subject": subject, "eligible": not reasons, "score": score,
                     "rejection_reasons": reasons, "words": len(subject.split()),
                     "length_prior": "within 2–6 words" if 2 <= len(subject.split()) <= 6 else "outside soft prior; no automatic penalty",
                     "response_tiebreak": bool(c.get("response_ids")) and bool(c.get("response_reason"))})
    return rows


def rank_pairs(subjects, bodies, retrieval, body_critic, subject_critic, packet=None):
    body_results = rank(bodies, retrieval, body_critic, packet)
    sr = rank_subjects(subjects, retrieval, subject_critic, is_reply=bool((packet or {}).get("current_thread")))
    pairs = []
    for body in body_results["candidates"]:
        if not body["eligible"]:
            continue
        for subject in sr:
            if not subject["eligible"] or body["id"] not in subject_critic[subject["id"]].get("compatible_body_ids", []):
                continue
            pairs.append({"body_id": body["id"], "subject_id": subject["id"],
                          "score": .75*body["score"] + .25*subject["score"],
                          "response_tiebreak": body["response_tiebreak"] or subject["response_tiebreak"]})
    pairs.sort(key=lambda x: x["score"], reverse=True)
    winner = max((p for p in pairs if pairs[0]["score"]-p["score"] <= .10), key=lambda p:(p["response_tiebreak"],p["score"])) if pairs else None
    selected = None
    if winner:
        body = next(b for b in bodies if b["id"] == winner["body_id"])
        subject = next(s for s in subjects if s["id"] == winner["subject_id"])
        selected = {**body, "subject": subject["subject"]}
    return {"winner": winner, "selected": selected, "pairs": pairs, "subjects": sr, "bodies": body_results,
            "reward": "Useful human responses among comparable contexts; opens are not scored", "response_probability": None}
