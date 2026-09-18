"""Local, passive Sent/thread store. No approval labels, network client or sender."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
from sender import route_sender_mode, select_sender_context

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ACCOUNTS = {"gordienko.adg@gmail.com", "andrew@gnk.software", "andrew.g@outagehub.ca", "andrew@wapahki.com"}
USEFUL = {"routing", "technical_answer", "positive_interest", "meeting_proposed", "meeting_confirmed", "next_step"}


def norm(value):
    return re.sub(r"[^\w@.]+", " ", str(value).casefold()).strip()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def original_body(body):
    # Preserve sentence boundaries, punctuation, paragraph spacing and short replies.
    body = body.replace("\r\n", "\n")
    return re.split(r"(?m)^On .{5,250}wrote:\s*$|^-{3,}\s*(?:Original Message|Forwarded message).*?$", body)[0].strip()


def excluded(m):
    text = (m.get("subject", "") + " " + " ".join(m.get("labels", []))).casefold()
    if any(x in text for x in ("apollo mailwarming", "blocklist check test")) or re.search(r"\bwbx\b", text):
        return True
    if m.get("kind") in {"automatic", "bounce", "out_of_office", "self", "draft"}:
        return True
    targets = {r.casefold() for r in m.get("recipients", [])}
    return m.get("sender", "").casefold() in ACCOUNTS and bool(targets) and targets <= ACCOUNTS


def infer_context(m, preceding):
    text = m["body"].casefold()
    objective = "unknown"
    if re.search(r"(?:stop by|visit|come by|tour)", text):
        objective = "research_visit"
    if re.search(r"(?:would|does).{0,45}(?:am|pm|monday|tuesday|wednesday|thursday|friday).{0,35}work|see you at|video this week", text):
        objective = "schedule"
    if re.search(r"(?:acquir|acquisition|dollar figure|price range)", text):
        objective = "acquisition"
    if re.search(r"(?:api|pricing|customer)", text) and objective == "unknown":
        objective = "customer"
    if re.search(r"(?:investor|fundraising|deck)", text) and objective == "unknown":
        objective = "investor"
    relationship = "existing" if any(x.get("kind") == "human" for x in preceding) else "unknown"
    if relationship == "unknown" and preceding:
        relationship = next((x.get("context", {}).get("relationship") for x in reversed(preceding) if x.get("context", {}).get("relationship")), "unknown")
    if not preceding and re.search(r"spoke (?:over|on) the phone|suggested i reach out|recommended i", text):
        relationship = "warm"
    return {"objective": objective, "relationship": relationship}


def infer_outcome(sent, later):
    """Conservative baseline; ambiguous semantics are resolved by Codex from the thread."""
    replies = [m for m in later if m.get("kind") == "human" and not excluded(m)]
    if not replies:
        return {"type": "no_visible_reply", "replied": None, "confidence": "unknown", "evidence": [], "censored": True}
    # The first downstream human response, never all later success credited to every send.
    reply = replies[0]
    if any(m.get("kind") == "sent" for m in later[:later.index(reply)]):
        return {"type": "reply_attribution_uncertain", "replied": None, "confidence": "unknown", "evidence": [], "censored": True}
    txt = reply["body"].casefold()
    rules = [
        ("polite_decline", r"not interested|not a fit|won't be able|cannot help|can't help"),
        ("routing", r"(?:sent|forwarded|passed) this to|(?:reach out|contact|speak) (?:directly )?to|introduc(?:e|ing) you"),
        ("meeting_confirmed", r"see you at \d|yes.{0,20}\d\s*(?:pm|am)"),
        ("meeting_proposed", r"let.s (?:try and )?get together|set it up for|(?:call|meet).{0,30}(?:tuesday|wednesday|thursday|friday)"),
        ("positive_interest", r"(?:would be|we.re|i.m) interested|happy to discuss"),
    ]
    kind = next((kind for kind, pattern in rules if re.search(pattern, txt)), "human_reply")
    return {"type": kind, "replied": True, "confidence": "medium" if kind != "human_reply" else "low",
            "observed_outcome_at": reply.get("sent_at"),
            "evidence": [{"message_id": reply["id"], "quote": reply["body"][:600]}],
            "attribution": "next visible human message in thread; association, not proof of wording effect",
            "censored": False}


def validate_annotation(annotation, messages):
    ids = {m["id"]: m for m in messages}
    if annotation.get("confidence") not in {"low", "medium", "high", "unknown"}:
        raise ValueError("Annotation needs confidence")
    if not annotation.get("evidence"):
        raise ValueError("Annotation needs source message evidence")
    for e in annotation["evidence"]:
        if e.get("message_id") not in ids or not e.get("quote") or e["quote"] not in ids[e["message_id"]]["body"]:
            raise ValueError("Annotation quote must occur in a captured source message")


def save_thread(thread, data=DATA):
    if thread.get("account") not in ACCOUNTS or not thread.get("source") or not thread.get("id"):
        raise ValueError("Thread requires known account, source and id")
    if not thread.get("observed_at") or not isinstance(thread.get("messages"), list):
        raise ValueError("Thread requires observed_at and ordered messages")
    seen = set()
    for pos, m in enumerate(thread["messages"]):
        if not m.get("id") or m["id"] in seen or not isinstance(m.get("body"), str):
            raise ValueError("Unique message IDs and original bodies required")
        if m.get("kind") not in {"sent", "human", "automatic", "bounce", "out_of_office", "self", "unknown"}:
            raise ValueError("Message kind must reflect visible sender/headers")
        if m["kind"] == "sent" and m.get("sender", "").casefold() not in ACCOUNTS:
            raise ValueError("Sent voice source must be one of Andrew's accounts")
        seen.add(m["id"])
        for annotation in m.get("annotations", {}).values():
            validate_annotation(annotation, thread["messages"])
        if "outcome" in m.get("annotations", {}):
            a = m["annotations"]["outcome"]
            if a["value"].get("type") not in USEFUL | {"polite_decline", "human_reply"}:
                raise ValueError("Unsupported human outcome type")
            downstream = {r["id"] for r in thread["messages"][pos + 1:] if r["kind"] == "human" and not excluded(r)}
            if not {e["message_id"] for e in a["evidence"]} <= downstream:
                raise ValueError("Human outcome evidence must be downstream human mail")
    target = data / "threads" / (digest(thread["account"] + thread["id"]) + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(thread, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(target)
    return target


def records(data=DATA):
    result = []
    for file in sorted((data / "threads").glob("*.json")):
        thread = json.loads(file.read_text())
        messages = thread["messages"]
        for i, m in enumerate(messages):
            if m["kind"] != "sent" or excluded(m):
                continue
            annotations = m.get("annotations", {})
            context = {**thread.get("context", {}), **infer_context(m, messages[:i]), **m.get("context", {})}
            if "context" in annotations:
                context.update(annotations["context"]["value"])
            context["sender_mode"] = route_sender_mode(context)
            outcome = infer_outcome(m, messages[i + 1:])
            if "outcome" in annotations:
                a = annotations["outcome"]
                outcome = {**a["value"], "confidence": a["confidence"], "evidence": a["evidence"], "method": "Codex thread classification"}
            result.append({"id": m["id"], "thread_id": thread["id"], "account": thread["account"],
                           "recipient": m.get("recipients", []), "context": context,
                           "subject": m.get("subject", thread.get("subject", "")),
                           "body": original_body(m["body"]), "sent_at": m.get("sent_at", ""),
                           "source": thread["source"], "usage": "full" if m.get("complete", True) else "fragment",
                           "outcome": outcome, "thread_complete": thread.get("complete", False)})
    # Earlier captures were real sent excerpts, not approved/draft examples. Mark their limits.
    for f in sorted((data / "legacy-excerpts").glob("*.json")):
        r = json.loads(f.read_text()); m = r["metadata"]
        if m.get("QUALITY") == "excluded":
            continue
        result.append({"id": m["ID"], "thread_id": m.get("PROVENANCE", m["ID"]), "account": m.get("ACCOUNT", "unknown"),
                       "recipient": [m.get("RECIPIENT", "")], "context": {"type": m["TYPE"], "relationship": m["RELATIONSHIP"], "objective": m["INTENT"], "organization": m.get("ORGANIZATION", "")},
                       "subject": m.get("SUBJECT", ""), "body": r["body"], "source": m.get("PROVENANCE", ""), "sent_at": "", "usage": "fragment",
                       "outcome": {"type": "unknown", "evidence": [], "confidence": "unknown"}})
    # Excerpts contained in a complete captured message are not independent examples.
    full = [r for r in result if r["usage"] == "full"]
    return [r for r in result if r["usage"] == "full" or not any(norm(r["body"]) in norm(x["body"]) for x in full)]


def select_task_draft(context):
    """Keep a task-local seed separate from sent voice and outcome evidence."""
    for key in ("supplied_draft", "existing_task_draft"):
        draft = context.get(key)
        if draft is None:
            continue
        if not isinstance(draft, dict) or not all(isinstance(draft.get(k), str) and draft[k].strip() for k in ("body", "source")):
            raise ValueError(f"{key} requires original body and source")
        if "subject" in draft and not isinstance(draft["subject"], str):
            raise ValueError(f"{key} subject must be text")
        return {"kind": key, "body": draft["body"], "source": draft["source"], "subject": draft.get("subject", "")}
    return None


def retrieve(context, data=DATA, limit=5):
    task_draft = select_task_draft(context)
    sender_context = select_sender_context(context)
    context = {**context, "sender_mode": sender_context["mode"]}
    bank = records(data)
    weights = {"relationship": 20, "objective": 28, "type": 12, "department": 8,
               "seniority": 6, "industry": 4, "company_size": 3, "organization": 10, "sender_mode": 12}
    query = set(norm(context.get("thought", "")).split())
    target = norm(context.get("recipient", ""))
    ranked = []
    for r in bank:
        same = bool(target) and target in {norm(x) for x in r["recipient"]}
        matches = [k for k in weights if context.get(k) not in (None, "", "unknown") and norm(context[k]) == norm(r["context"].get(k, ""))]
        relevance = sum(weights[k] for k in matches) + min(8, len(query & set(norm(r["body"]).split())))
        if not same and not matches and not query.intersection(set(norm(r["body"]).split())):
            continue
        # No outcome or manual approval appears in the voice score.
        ranked.append(((same, relevance, r["usage"] == "full", r.get("sent_at", "")), {**r, "match_reasons": matches + (["same_recipient"] if same else [])}))
    ranked.sort(key=lambda x: x[0], reverse=True)
    voice, hashes = [], set()
    for _, r in ranked:
        h = digest(norm(r["body"]))
        if h in hashes:
            continue
        hashes.add(h)
        voice.append({k: v for k, v in r.items() if k != "outcome"})
        if len(voice) >= limit:
            break
    outcomes, threads = [], set()
    for _, r in ranked:
        # Compare same relationship AND objective. Unknown is not a match or a failure.
        if not all(context.get(k) not in (None, "", "unknown") and norm(context[k]) == norm(r["context"].get(k, "")) for k in ("relationship", "objective")):
            continue
        o = r["outcome"]
        if o["type"] not in USEFUL or o.get("confidence") not in {"medium", "high"} or not o.get("evidence"):
            continue
        tid = (r["account"], r["thread_id"])
        if tid in threads:
            continue
        threads.add(tid); outcomes.append(r)
        if len(outcomes) >= limit:
            break
    same_history = [r for r in bank if target and target in {norm(x) for x in r["recipient"]}]
    same_history.sort(key=lambda r: r.get("sent_at", ""), reverse=True)
    gold=[json.loads(p.read_text()) for p in (Path(__file__).resolve().parents[1]/'corpus/gold').glob('*.json')]
    gold=[g for g in gold if g.get('sender_mode')==sender_context['mode']]
    return {"approved_exemplars":gold,"task_draft": task_draft, "sender_context": sender_context,
            "drafting_priority": ["current supplied or existing task-specific draft", "same-recipient history", "highly similar sent emails", "broader sent-mail patterns"],
            "voice_examples": voice, "response_examples": outcomes, "recipient_history": same_history[:limit],
            "coverage": {"records": len(bank), "full_messages": sum(r["usage"] == "full" for r in bank), "selection": "task-time sample, not exhaustive Gmail sync"},
            "response_probability": None, "method": "metadata plus lexical retrieval; Codex reranks contextual fit"}


def index(data=DATA):
    data.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(data / "history.sqlite3") as db:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mail_fts USING fts5(id UNINDEXED, subject, body, recipient, context)")
        db.execute("DELETE FROM mail_fts")
        for r in records(data):
            db.execute("INSERT INTO mail_fts VALUES (?, ?, ?, ?, ?)", (r["id"], r["subject"], r["body"], ", ".join(r["recipient"]), json.dumps(r["context"])))
    return len(records(data))
