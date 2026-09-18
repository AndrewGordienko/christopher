"""MBOX adapter using pinned RAGmail parsing, preserving short conversational mail."""
import sys
from pathlib import Path
from email.utils import getaddresses
from html.parser import HTMLParser
from datetime import datetime, timezone
from history import ROOT, DATA, ACCOUNTS, digest, save_thread

sys.path.insert(0, str(ROOT / "third_party/ragmail"))
from email_parser import EmailParser
from mbox_reader import MboxReader


class Parser(EmailParser):
    def _clean_body(self, body):
        return body.replace("\r\n", "\n").strip()

    def _parse_address_list(self, addresses):
        return [addr for _, addr in getaddresses([addresses or ""]) if addr]


class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "blockquote"}:
            self.skip += 1
        if not self.skip and tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "blockquote"}:
            self.skip = max(0, self.skip - 1)
        if not self.skip and tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def ingest_mbox(path, account, data=DATA):
    if account not in ACCOUNTS:
        raise ValueError("Specify one of Andrew's verified accounts")
    parser = Parser(); messages = []; parents = {}

    def root(x):
        parents.setdefault(x, x)
        if parents[x] != x:
            parents[x] = root(parents[x])
        return parents[x]

    for raw in MboxReader(path):
        p = parser.parse(raw)
        mid = (p.message_id or digest(raw.as_string())).strip()
        root(mid)
        for related in p.references + ([p.in_reply_to] if p.in_reply_to else []):
            parents[root(mid)] = root(related.strip())
        gm = raw.get("X-GM-THRID")
        if gm:
            parents[root(mid)] = root("gmail:" + gm)
        body = p.body_plain
        if not body and p.body_html:
            html = HtmlText(); html.feed(p.body_html); body = "".join(html.parts).strip()
        sender = p.from_address.casefold()
        kind = "sent" if sender in ACCOUNTS else "human"
        if raw.get("Auto-Submitted", "no").lower() != "no" or raw.get("X-Autoreply") or raw.get("X-Autorespond"):
            kind = "automatic"
        if raw.get_content_type() == "multipart/report" or "mailer-daemon" in sender:
            kind = "bounce"
        if any(x in p.subject.casefold() for x in ("out of office", "automatic reply", "auto-reply", "vacation reply")):
            kind = "out_of_office"
        if "draft" in {x.casefold() for x in p.labels}:
            continue
        messages.append({"id": mid, "sender": sender, "recipients": p.to_addresses + p.cc_addresses, "kind": kind,
                         "sent_at": p.date.isoformat() if p.date else "", "body": body, "subject": p.subject, "labels": p.labels})
    groups = {}
    for m in messages:
        groups.setdefault(root(m["id"]), {})[m["id"]] = m
    count = 0
    for tid, values in groups.items():
        rows = sorted(values.values(), key=lambda m: m["sent_at"])
        if not any(m["kind"] == "sent" for m in rows):
            continue
        save_thread({"id": "mbox:" + tid, "account": account, "source": str(Path(path).resolve()),
                     "observed_at": datetime.now(timezone.utc).isoformat(), "complete": False,
                     "coverage_note": "Complete within this archive only; absence of replies remains censored",
                     "subject": rows[0]["subject"], "messages": rows}, data)
        count += 1
    return {"messages_parsed": len(messages), "threads_saved": count}
