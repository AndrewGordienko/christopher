"""Evidence-aware timezone resolution and recipient-local recommendations, never sends."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from pathlib import Path
import hashlib
import json
import time

POLICY = Path(__file__).resolve().parents[1] / "policies/scheduling.json"
PRIORITY = {"person_location": 0, "apollo_person_location": 0, "relevant_office": 1, "relevant_facility": 1, "company_hq": 2, "apollo_timezone": 3}

def validate_send_time(context, send_at, now=None):
    """Validate the actual queued instant, not a stale recommendation or sender time."""
    issues=[]
    def issue(label): issues.append({'code':'send_time','label':label})
    now=now or datetime.now(timezone.utc)
    try:
        if not known_zone(context.get('timezone')): raise ValueError('Recipient timezone unresolved')
        if context.get('timezone_uncertain') or context.get('timezone_source') not in PRIORITY or not context.get('timezone_source_id'):
            raise ValueError('Recipient timezone needs sourced confirmation')
        if not send_at: raise ValueError('Choose a send time before scheduling')
        dt=datetime.fromisoformat(send_at.replace('Z','+00:00'))
        if dt.tzinfo is None: raise ValueError('Send time needs an explicit offset')
        policy=context.get('schedule_policy') or json.loads(POLICY.read_text())
        local=dt.astimezone(ZoneInfo(context['timezone']))
        if dt<=now+timedelta(minutes=policy.get('minimum_lead_minutes',15)): issue('Choose a future slot with enough scheduling lead time')
        if local.weekday() not in policy['weekdays']: issue('Send time falls outside recipient-local working days')
        minute=local.hour*60+local.minute
        lo,hi=[int(v.split(':')[0])*60+int(v.split(':')[1]) for v in (policy['window_start'],policy['window_end'])]
        if not lo<=minute<=hi: issue(f'Send time is {local:%H:%M %Z}; outside recipient-local window {policy["window_start"]}–{policy["window_end"]}')
    except (ValueError,TypeError,KeyError,ZoneInfoNotFoundError) as exc: issue(str(exc) or 'Invalid send time')
    return issues


def known_zone(name):
    if not isinstance(name, str) or "/" not in name:
        return False
    try:
        ZoneInfo(name)
        return True
    except ZoneInfoNotFoundError:
        return False


def geocode(place, cache):
    # Geocode a public city/region, not a person's street address. Cache avoids repeat calls.
    parts = [str(place.get(k) or "").strip() for k in ("city", "state", "country")]
    if not parts[0] or not parts[2]:
        return None
    query = ", ".join(p for p in parts if p)
    key = hashlib.sha256(query.encode()).hexdigest()[:20]
    file = cache / (key + ".json")
    if file.exists():
        return json.loads(file.read_text())
    cache.mkdir(parents=True, exist_ok=True)
    throttle = cache / "last-request"
    if throttle.exists():
        time.sleep(max(0, 1.1 - (time.time() - float(throttle.read_text()))))
    url = "https://nominatim.openstreetmap.org/search?" + urlencode({"q": query, "format": "jsonv2", "limit": 2, "addressdetails": 1})
    throttle.write_text(str(time.time()))
    try:
        with urlopen(Request(url, headers={"User-Agent": "AndrewOutreachResearch/1.0 (local research tool)", "Accept-Language": "en"}), timeout=20) as response:
            results = json.load(response)
    except Exception:
        return None
    # Ambiguity is a research task, not permission to use the first city with that name.
    if len(results) != 1:
        return None
    row = results[0]
    if row.get("class") not in {"place", "boundary"}:
        return None
    resolved = {"latitude": float(row["lat"]), "longitude": float(row["lon"]), "geocode_source": url,
                "geocode_label": row.get("display_name"), "query": query}
    file.write_text(json.dumps(resolved))
    return resolved


def resolve_timezone(locations, cache=None, geocoder=geocode):
    errors = []
    for place in sorted(locations, key=lambda x: PRIORITY.get(x.get("source"), 99)):
        if place.get('source') not in PRIORITY or place.get('verified') is False or place.get('uncertain'):
            errors.append('Location source is unknown, unverified or ambiguous')
            continue
        if not place.get("source_id"):
            errors.append("Location lacks provenance")
            continue
        name = place.get("time_zone") or place.get("timezone")
        geo = None
        if not known_zone(name):
            if place.get("latitude") is not None and place.get("longitude") is not None:
                geo = place
            elif cache:
                geo = geocoder(place, cache)
            if geo:
                try:
                    from timezonefinder import TimezoneFinder
                    name = TimezoneFinder().timezone_at(lat=float(geo["latitude"]), lng=float(geo["longitude"]))
                except (ImportError, ValueError):
                    errors.append("Coordinate timezone lookup unavailable")
        if known_zone(name):
            return {"timezone": name, "timezone_source": place["source"], "source_id": place["source_id"],
                    "location": ", ".join(str(place[k]) for k in ("city", "state", "country") if place.get(k)),
                    "geocode_source": (geo or {}).get("geocode_source"), "assumed_office_location": place["source"] in {"relevant_office", "relevant_facility", "company_hq"}}
    return {"timezone": None, "timezone_source": "unknown", "reason": "Resolve recipient/office location; sender timezone is not a fallback", "notes": errors}


def recommend_send(resolved, recipient_id, now=None, policy=None, occupied=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Current time must be timezone-aware")
    policy = policy or json.loads(POLICY.read_text())
    if not resolved.get("timezone"):
        return {**resolved, "recommended_send_local": None, "recommended_send_utc": None, "status": "timezone_unknown"}
    tz = ZoneInfo(resolved["timezone"])
    def minutes(value):
        h, m = map(int, value.split(":"))
        if not 0 <= h <= 23 or not 0 <= m <= 59:
            raise ValueError("Invalid send window")
        return h * 60 + m
    start, end = minutes(policy["window_start"]), minutes(policy["window_end"])
    days = policy["weekdays"]
    if start >= end or not days or any(type(d) is not int or not 0 <= d <= 6 for d in days):
        raise ValueError("Invalid recipient-local scheduling policy")
    earliest = now + timedelta(minutes=max(0, policy.get("minimum_lead_minutes", 30)))
    local_day = earliest.astimezone(tz).date()
    if any(x.tzinfo is None for x in (occupied or [])):
        raise ValueError('Occupied slots must be timezone-aware')
    occupied = sorted(x.astimezone(timezone.utc) for x in (occupied or []))
    for n in range(15):
        day = local_day + timedelta(days=n)
        if day.weekday() not in days:
            continue
        minute = start
        if day == earliest.astimezone(tz).date():
            local_earliest = earliest.astimezone(tz)
            minute = max(minute, local_earliest.hour*60 + local_earliest.minute + bool(local_earliest.second or local_earliest.microsecond))
        choices = []
        gap = timedelta(minutes=max(1, policy.get('minimum_spacing_minutes', 10)))
        for candidate_minute in range(minute, end+1):
            candidate = datetime(day.year, day.month, day.day, candidate_minute//60, candidate_minute%60, tzinfo=tz)
            # Reject imaginary local times and actual queue collisions, including other zones.
            utc = candidate.astimezone(timezone.utc)
            if utc.astimezone(tz).replace(tzinfo=None) != candidate.replace(tzinfo=None) or candidate < earliest:
                continue
            if any(abs(utc-other) < gap for other in occupied):
                continue
            if sum(other.date()==utc.date() for other in occupied)>=policy.get('daily_limit',30): continue
            hourly=sum(abs((utc-other).total_seconds())<3600 for other in occupied)
            if hourly>=policy.get('hourly_limit',6): continue
            # Avoid extending an existing metronomic run. Round minutes alone are fine.
            nearby=sorted(occupied+[utc]);i=nearby.index(utc)
            regular=False
            for j in range(max(0,i-3),min(i+1,len(nearby)-3)):
                gs=[(b-a).total_seconds() for a,b in zip(nearby[j:j+4],nearby[j+1:j+4])]
                if len(gs)==3 and len(set(gs))==1 and gs[0]<=3600: regular=True
            if regular: continue
            # Stable dispersion within valid windows; this is capacity allocation,
            # not a claim that a particular minute is more human or more effective.
            tie=int(hashlib.sha256(f'{recipient_id}/{day}/{candidate_minute}'.encode()).hexdigest()[:12],16)
            choices.append((hourly,tie,candidate))
        if not choices: continue
        dt=min(choices,key=lambda x:x[:2])[2]
        return {**resolved, "recommended_send_local": dt.isoformat(), "recommended_send_utc": dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "timezone_abbreviation": dt.tzname(), "status": "recommended_only", "policy": policy,
                "rationale": "Distributed within recipient-local working hours, subject to mailbox capacity and spacing; no minute is claimed optimal. Requires individual approval."}
    raise ValueError("No valid future window under the scheduling policy")
