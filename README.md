# Christopher

One local operating UI for Contract Work, Wapahki and OutageHub. Start with a goal in Codex, or save a mission through the command dialog in the app. Research, source validation, historical email retrieval and drafting are separate stages. Everything is draft-only.

```sh
npm ci
npm run build
npm start
```

Open **http://localhost:4173**. Today shows the action queue; Accounts, People, Inbox, Schedule, Research, Pipeline and Analytics share the same records. The account detail has sources, working hypotheses, history used, all three emails and an activity timeline. Tables support sorting, search and stage filters. Local approvals review copy; they do not authorize or transmit email.

## Current demonstration

Global Fishing Watch has three current researched contacts and Apollo-verified work emails. All three drafts preserve Andrew’s supplied technical-contract seed; only the greeting changes. Eight subjects were evaluated per person. David is the first contact, Fernando and Paul are held backups. No GFW sends or replies have been observed. Gmail searches found unsent drafts only. Four full Sent examples calibrate cadence; there is no exact cold-contract outcome match.

Ecolomondo Hawkesbury is a separate Wapahki tire-processing facility research record. Its captured automatic-production evidence is from2025, so current equipment/operations, contacts and data access remain research tasks. It has no invented drafts, contacts, fit score or claimed pilot.

## How a mission runs

The [skill](skills/andrew-email-style/SKILL.md) is the controller. [Mission and signal instructions](skills/andrew-email-style/references/missions-and-signals.md) define qualification, account/facility/person research, sender context, Apollo, subjects and scheduling. Codex executes the reasoning and web/Gmail interactions; the Python boundary validates and persists results. There is no separate fine-tuned model or trained reply-probability model.

```sh
.venv/bin/python skills/andrew-email-style/scripts/outbound.py mission "Find 30 organizations where I can apply my AI skills for good on bounded contract work; find the best 3 people at each and draft outreach. Do not send."
.venv/bin/python skills/andrew-email-style/scripts/outbound.py next CAMPAIGN
```

Contract projects optimize for useful bounded work, signed value and funded payment. Wapahki qualifies specific facilities, including MRFs and tire recycling/retreading, for visits and recovery data before pilots. OutageHub requires an explicit external-grid-data gap and current competitive/product evidence. A job, regulatory target, investment or outage incident changes ranking only when the account also fits.

Public research must retain captured source IDs and exact supporting quotes. Facts, hypotheses and unknowns stay distinct. A producer obligation is not automatically a processor obligation. An approved headcount does not prove discretionary contract budget. Research stays mostly invisible in email prose.

## Follow-ups and nightly preparation

[Follow-up procedure and capture schemas](skills/andrew-email-style/references/nightly-workflow.md).

SQLite `.runtime/outbound.sqlite3` owns contact/thread state, touches, replies, pending actions, activities and job/pressure signals. JSON/Markdown hold research and drafts, not the truth about whether mail was sent.

- Eligibility: initial, D3–4, D8–10, optional D15–18. Generate each follow-up only when due, after a fresh full-thread/research check and SEND / WAIT / COMPLETE decision. SEND means prepare for review.
- Human replies cancel pending no-response follow-ups; opt-outs, bounces and explicit declines stop the address. OOO defers to after a known return date or a later re-check.
- Keep sender, thread and subject. Backups and follow-ups compete for the same capacity; maximum one account/address per queue day.
- Default capacity30 is shared across all workspaces. Unknown timezone, stale mail, unqualified account, missing draft or missing follow-up reason creates a hold, not a placeholder email.
- Actual outcomes drive touch/role/engine analytics. No tracking pixels, fabricated conversion percentages or automatic sending.

A local LaunchAgent `ca.andrew.outbound-prepare` is installed to prepare around **23:00 Europe/London**, once per day. It checks the time every15minutes, uses a process lock and starts `codex exec` with the nightly instructions. It requires the Mac awake, Codex authentication and accessible Chrome/Gmail. The deterministic dry run has been tested; no complete unattended Gmail/research run has occurred yet. Runs, logs and access limitations live privately under `.runtime/`. Access failures leave stale contacts held.

```sh
.venv/bin/python skills/andrew-email-style/scripts/operations.py import
.venv/bin/python skills/andrew-email-style/scripts/operations.py status
.venv/bin/python skills/andrew-email-style/scripts/nightly.py --dry-run
# Run the complete preparation task now (reads Gmail/research; does not send):
.venv/bin/python skills/andrew-email-style/scripts/nightly.py
```

Pause the installed job with `launchctl bootout gui/$(id -u)/ca.andrew.outbound-prepare`. No sender daemon is installed.

## Dependencies and integrations

React, TanStack Table8 and Radix dialog primitives power the small local app. Node serves only compiled UI files and curated API projections; full Sent Mail, credentials, raw research captures and campaign directories are not static web routes. SQLite needs no database server.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
python3 -m venv .venv-jobs
.venv-jobs/bin/python -m pip install -r requirements-jobs.txt
```

`timezonefinder` plus `zoneinfo` handles public location resolution and daylight-saving conversion. Unknown recipient location does not fall back to Andrew’s timezone. Default local windows are a configurable prior, not a learned optimum.

Apollo uses the protected local file `~/.config/goran-email/apollo-api-key` (or `APOLLO_API_KEY_FILE`), then the environment fallback. Only the researched top three people at qualified accounts are enriched; work email only, cached30days, no paid retry loops. Provider verification is not a delivery guarantee.

Pinned MIT **ats-jobs** supplies ATS ingestion, and **ats-api-reference** is retained with its license/provenance. Full descriptions and raw provider results are preserved; changed/new/closed roles are diffed. Polling errors do not close jobs. **JobSpy** is an optional wider-discovery adapter in a separate environment because its NumPy pin conflicts with timezonefinder. No job application workflow is installed.

UI/research references and pinned upstream commit IDs are under the skill’s references and `third_party/hiring-provenance.json`. No upstream CRM or email-sending service was imported.

## Validation

```sh
python3 -m unittest discover -s skills/andrew-email-style/tests
node --test skills/andrew-email-style/third_party/ats-jobs/test/*.test.js
npm run build
```

Current local checks cover drafting priority, sender routing, research provenance, mission routing, timezone/DST behavior, shared queue capacity, cancellation/OOO, thread continuity, approval isolation, subject bans, facility identity, grid-data qualification and hiring/pressure safeguards. Browser verification covers the shared UI and GFW comparison. Private artifacts stay in ignored `campaigns/`, skill `data/` and `.runtime/`.
