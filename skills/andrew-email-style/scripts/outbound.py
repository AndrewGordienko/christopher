#!/usr/bin/env python3
"""JSON boundary for Codex's conversational account-to-pilot workflow. Draft-only."""
import argparse
import json
from pathlib import Path
import sys
from history import DATA, USEFUL, records, index, retrieve, save_thread
from research import campaign, add_source, save_account, writer_packet, read_sources, write_json, slug


def read(path):
    return json.loads(Path(path).read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("campaign"); c.add_argument("name"); c.add_argument("--goal", required=True)
    m = sub.add_parser("mission"); m.add_argument("goal"); m.add_argument("--campaign"); m.add_argument("--plan")
    n = sub.add_parser("next"); n.add_argument("campaign")
    v = sub.add_parser("review-queue"); v.add_argument("campaign", nargs="?")
    d = sub.add_parser("apollo-search"); d.add_argument("campaign"); d.add_argument("account"); d.add_argument("filters")
    d = sub.add_parser("apollo-enrich"); d.add_argument("campaign"); d.add_argument("account"); d.add_argument("person"); d.add_argument("--refresh", action="store_true")
    s = sub.add_parser("recommend-time"); s.add_argument("campaign"); s.add_argument("account"); s.add_argument("person")
    j = sub.add_parser("rank-message"); j.add_argument("campaign"); j.add_argument("account"); j.add_argument("person")
    s = sub.add_parser("source"); s.add_argument("campaign"); s.add_argument("json")
    a = sub.add_parser("account"); a.add_argument("campaign"); a.add_argument("json")
    w = sub.add_parser("prepare"); w.add_argument("campaign"); w.add_argument("account"); w.add_argument("person_id"); w.add_argument("context")
    i = sub.add_parser("thread"); i.add_argument("json")
    m = sub.add_parser("mbox"); m.add_argument("path"); m.add_argument("--account", required=True)
    r = sub.add_parser("retrieve"); r.add_argument("context")
    sub.add_parser("index")
    o = sub.add_parser("outcomes"); o.add_argument("--after"); o.add_argument("--useful", action="store_true")
    t = sub.add_parser("status"); t.add_argument("campaign", nargs="?")
    e = sub.add_parser("rank"); e.add_argument("candidates"); e.add_argument("retrieval"); e.add_argument("critic"); e.add_argument("--packet"); e.add_argument("--save", type=Path)
    args = p.parse_args()
    if args.command == "mission":
        from mission import create_mission
        result = create_mission(args.goal, args.campaign, read(args.plan) if args.plan else None)
    elif args.command == "next":
        from mission import next_actions
        result = next_actions(campaign(args.campaign))
    elif args.command == "review-queue":
        from mission import review_campaign, review_catalog
        result = review_campaign(campaign(args.campaign)) if args.campaign else review_catalog()
    elif args.command == "apollo-search":
        from apollo import search_people
        result = search_people(campaign(args.campaign), args.account, read(args.filters))
    elif args.command == "apollo-enrich":
        from apollo import enrich_selected
        result = enrich_selected(campaign(args.campaign), args.account, args.person, args.refresh)
    elif args.command == "recommend-time":
        from scheduling import resolve_timezone, recommend_send
        from mission import validate_contact
        path = campaign(args.campaign)
        account = path / "accounts" / slug(args.account)
        folder = account / slug(args.person)
        expected = next(p for p in read(account / "research.json")["stakeholders"] if p["id"] == args.person)
        contact = validate_contact(read(folder / "contact.json"), read_sources(path), expected)
        result = recommend_send(resolve_timezone(contact.get("location_candidates", []), path / "geocode-cache"), args.person)
        from opportunities import contact_release
        people = [{**p,"outcome":read(account / slug(p["id"]) / "outcome.json") if (account / slug(p["id"]) / "outcome.json").exists() else {"type":"not_sent"}} for p in read(account / "research.json")["stakeholders"]]
        release = contact_release(expected["rank"], people)
        if release["status"] != "eligible": result.update(release); result.update(recommended_send_local=None,recommended_send_utc=None)
        write_json(folder / "schedule.json", result)
    elif args.command == "rank-message":
        from subjects import rank_pairs
        folder = campaign(args.campaign) / "accounts" / slug(args.account) / slug(args.person)
        current_brief = read(folder.parent / 'research.json')
        if current_brief.get('engine') == 'wapahki_facility':
            writer_packet(current_brief, read_sources(campaign(args.campaign)), args.person)
        result = rank_pairs(read(folder / "subject-candidates.json"), read(folder / "candidates.json"), read(folder / "retrieval.json"), read(folder / "critic.json"), read(folder / "subject-critic.json"), read(folder / "writer-packet.json"))
        write_json(folder / "subject-body-ranking.json", result)
        if result["selected"]:
            selected = result["selected"]
            (folder / "draft.md").write_text("Subject: " + selected["subject"] + "\n\n" + selected["body"].strip() + "\n")
    elif args.command == "campaign":
        result = {"path": str(campaign(args.name, args.goal))}
    elif args.command == "source":
        add_source(campaign(args.campaign), read(args.json)); result = {"saved": True}
    elif args.command == "account":
        result = {"path": str(save_account(campaign(args.campaign), read(args.json)))}
    elif args.command == "prepare":
        path = campaign(args.campaign)
        account = path / "accounts" / slug(args.account)
        brief = read(account / "research.json")
        packet = writer_packet(brief, read_sources(path), args.person_id)
        context = read(args.context)
        context.setdefault("recipient", packet["recipient"].get("email") or packet["recipient"]["name"])
        context.setdefault("organization", packet["company"]["name"])
        context.setdefault("objective", packet["objective"]["stage"])
        context.setdefault("department", packet["recipient"].get("department"))
        context.setdefault("seniority", packet["recipient"].get("seniority"))
        packet["andrew_thought"] = context.get("thought", "")
        packet["current_facts"] = context.get("current_facts", [])
        packet["current_thread"] = context.get("current_thread", [])
        retrieval = retrieve(context)
        packet["task_draft"] = retrieval["task_draft"]
        packet["sender_context"] = retrieval["sender_context"]
        packet["drafting_priority"] = retrieval["drafting_priority"]
        result = {"packet": packet, "retrieval": retrieval}
        write_json(account / slug(args.person_id) / "writer-packet.json", packet)
        write_json(account / slug(args.person_id) / "retrieval.json", result["retrieval"])
    elif args.command == "thread":
        result = {"path": str(save_thread(read(args.json)))}
        result["indexed"] = index()
    elif args.command == "mbox":
        from ingest import ingest_mbox
        result = ingest_mbox(args.path, args.account); result["indexed"] = index()
    elif args.command == "retrieve":
        result = retrieve(read(args.context))
    elif args.command == "index":
        result = {"indexed": index()}
    elif args.command == "outcomes":
        result = [r for r in records() if (not args.useful or r["outcome"]["type"] in USEFUL) and (not args.after or (r["outcome"].get("observed_outcome_at") or "") >= args.after)]
    elif args.command == "status":
        result = {"history": retrieve({})["coverage"], "mode": "draft_only", "refresh": "during Codex tasks", "background_sync": False}
        if args.campaign:
            path = campaign(args.campaign)
            result["accounts"] = [{"id": read(f)["company"]["id"], **read(f)["qualification"], "drafted": (f.parent / "drafts.md").exists()} for f in sorted(path.glob("accounts/*/research.json"))]
    else:
        from evaluate import rank
        candidates = read(args.candidates)
        result = rank(candidates, read(args.retrieval), read(args.critic), read(args.packet) if args.packet else None)
        if args.save and result["winner"]:
            winner = next(c for c in candidates if c["id"] == result["winner"])
            args.save.parent.mkdir(parents=True, exist_ok=True)
            args.save.write_text(("Subject: " + winner["subject"] + "\n\n" if winner.get("subject") else "") + winner["body"].strip() + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
