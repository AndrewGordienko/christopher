"""Apollo discovery and shortlist-only work-email enrichment. No sending endpoints."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import hashlib
import json
import os
import re
from research import add_source, read_sources, validate_brief, slug, write_json

BASE = "https://api.apollo.io/api/v1/"


def request(endpoint, payload):
    if endpoint not in {"mixed_people/api_search", "people/match"}:
        raise ValueError("Unsupported Apollo endpoint")
    key_file = Path(os.environ.get("APOLLO_API_KEY_FILE", str(Path.home() / ".config/goran-email/apollo-api-key")))
    key = key_file.read_text().strip() if key_file.exists() else os.environ.get("APOLLO_API_KEY", "").strip()
    if not key:
        raise ValueError("Apollo API key unavailable; use the connected Apollo tool/browser and record its results")
    req = Request(BASE + endpoint, data=json.dumps(payload).encode(), method="POST",
                  headers={"x-api-key": key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=35) as response:
            return json.load(response)
    except HTTPError as exc:
        # Never emit request headers or unreviewed error bodies containing account data.
        raise ValueError(f"Apollo returned HTTP {exc.code}; no automatic paid retry") from None
    except URLError:
        raise ValueError("Apollo connection failed; no automatic paid retry") from None


def receipt(path, endpoint, payload, response):
    at = datetime.now(timezone.utc).isoformat()
    text = json.dumps(response, ensure_ascii=False, sort_keys=True)
    sid = "apollo-" + hashlib.sha256((endpoint + at + text).encode()).hexdigest()[:18]
    add_source(path, {"id": sid, "url": BASE + endpoint, "observed_at": at, "tool": "Apollo API",
                      "tool_ref": sid, "text": text})
    write_json(path / "provider-results" / (sid + ".json"), {"endpoint": endpoint, "request": payload, "response": response, "observed_at": at})
    return sid, at


def search_people(path, account_id, filters):
    account = path / "accounts" / slug(account_id)
    brief = json.loads((account / "research.json").read_text())
    validate_brief(brief, read_sources(path))
    domain = brief["company"].get("domain")
    if not domain:
        raise ValueError("Resolve the account domain before Apollo discovery")
    payload = {**filters, "q_organization_domains_list": [domain], "page": filters.get("page", 1), "per_page": min(int(filters.get("per_page", 25)), 100)}
    response = request("mixed_people/api_search", payload)
    sid, at = receipt(path, "mixed_people/api_search", payload, response)
    people = response.get("people", [])
    result = {"source_id": sid, "observed_at": at, "people": people,
              "total_entries": response.get("total_entries"),
              "instruction": "Rank against current public research before enrichment. Search can match former employers; verify current company. Search results do not establish a verified email."}
    write_json(account / "apollo-discovery.json", result)
    return result


def normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def normalize_contact(person, expected, domain, sid, at):
    if not person or normalize_name(person.get("name")) != normalize_name(expected["name"]):
        raise ValueError("Apollo identity differs from the researched person; resolve before using contact data")
    org = person.get("organization") or {}
    found_domain = org.get("primary_domain") or urlparse(org.get("website_url") or "").hostname
    if not found_domain or found_domain.removeprefix("www.").casefold() != domain.removeprefix("www.").casefold():
        raise ValueError("Apollo current organization differs or is missing; resolve employer before using the email")
    email = person.get("email")
    if email and (not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or "email_not_unlocked" in email):
        email = None
    status = person.get("email_status") or "unknown"
    location = {k: person.get(k) for k in ("city", "state", "country", "time_zone", "latitude", "longitude") if person.get(k) is not None}
    location.update(source="apollo_person_location", source_id=sid)
    hq = {k: org.get(k) for k in ("city", "state", "country", "time_zone", "latitude", "longitude") if org.get(k) is not None}
    hq.update(source="company_hq", source_id=sid)
    return {"person_id": expected["id"], "name": expected["name"], "apollo_id": person.get("id"),
            "role": expected["role"], "apollo_role": person.get("title"),
            "email": email, "email_status": "verified" if email and status == "verified" else (status if email else "unavailable"),
            "email_verification_source": "Apollo", "source_id": sid, "observed_at": at,
            "location_candidates": [location, hq], "linkedin_url": person.get("linkedin_url"),
            "scope": "Work email only. Provider verification is not a delivery guarantee."}


def enrich_selected(path, account_id, person_id, force=False):
    account = path / "accounts" / slug(account_id)
    brief = json.loads((account / "research.json").read_text())
    validate_brief(brief, read_sources(path))
    selected = next((p for p in brief["stakeholders"] if p["id"] == person_id and p["rank"] in (1, 2, 3)), None)
    if brief["qualification"]["verdict"] != "yes" or not selected:
        raise ValueError("Enrichment is restricted to the ranked shortlist of a qualified account")
    target = account / slug(person_id) / "contact.json"
    if target.exists() and not force:
        old = json.loads(target.read_text())
        if old.get("source_id") in read_sources(path) and (datetime.now(timezone.utc) - datetime.fromisoformat(old["observed_at"])).days < 30:
            return {**old, "cached": True}
    domain = brief["company"].get("domain")
    if not domain:
        raise ValueError("Resolve the company domain before enriching")
    payload = {"name": selected["name"], "domain": domain, "reveal_personal_emails": False,
               "reveal_phone_number": False, "run_waterfall_email": False, "run_waterfall_phone": False}
    if selected.get("apollo_id"):
        payload["id"] = selected["apollo_id"]
    response = request("people/match", payload)
    sid, at = receipt(path, "people/match", payload, response)
    result = normalize_contact(response.get("person"), selected, domain, sid, at)
    write_json(target, result)
    return result
