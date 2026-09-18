# Three workspaces, one operating model

## Current cell gate (September 2026)

For new Morrow/Wapahki pilot outreach, [morrow-pilot-qualifier](../../morrow-pilot-qualifier/SKILL.md) and the other five linked stages in the main skill supersede older automation-only selection, plant-wide baseline offers and volume targets below. A scored QUALIFIED cell is required before writing; POSSIBLE means more research, HOLD means no outreach. Historic examples remain history. First scope: one cell, passive faults/actions/restored-state observation, repeatable human intervention time, then one separately authorized suitable recovery. Neither a robot installation nor downstream manual sorting proves recurring operator recovery. The UofT student identity is supported; a formal university research-project affiliation requires separate evidence.

Contract Work: interesting bounded problem → conversation → defined project → signed agreement → funded payment → delivery. Target $15k signed over21days; currency must be resolved for an actual agreement. Prefer two substantial bounded projects over many tiny ones. No pricing, consultant vocabulary or phases in first touch. Score current skill fit, interest, actual need, boundedness, ability to pay and technical reachability. A consulting board or job posting is not evidence this project has budget. After day5–7, prepare another qualified wave if fewer than three serious conversations; never invent opportunities to fill the funnel.

Wapahki: **facility**, not parent company, is the unit. Ontario/GTA first, then Canada. Distinguish material-recovery sorting, tire recycling, tire retreading and other process automation. Robot/AMR presence, PLC/HMI process lines, vision, shredding, milling, conveying, separation, pelletizing and bagging can all matter. Rank failure/recovery-data richness and accessibility, not robot count. Do not assert that a plant has frequent stops, accessible logs or classical robots without evidence. Preserve vendor/OEM/integrator/material/throughput/location unknowns. Target first visit/observation, then authorized read-only events, offline analysis, human-approved recovery suggestions, explicitly authorized bounded execution, deployment/customer. Permission at one stage does not authorize the next. For tire plants inspect PLC alarms, states, E-stops, VFD/motor/conveyor faults, AMR/vision events, operator resets, maintenance and timestamps. Ecolomondo Hawkesbury is a research priority, not proof of a pilot or current commissioning status.

OutageHub API: existing product/workflow → external-grid-data gap → product conversation → evaluation → integration → ARR. Telemetry can coexist with a need for utility context. Before qualifying, state exactly what receiving an event changes in an existing product or workflow. Resolve equal/better internal utility coverage and current alternatives; compare actual OutageHub capabilities/economics, not assumed Canada exclusivity. Product buyers for embedding, NOC/operations for operations, data/risk for analytics, partnerships for commercial feeds; CTO only when appropriate. Keep acquisition discussions separate from API sales. All capability, pricing, coverage and latency comparisons require current product evidence.

## Commands

For Wapahki, apply [benchmark-first pilot selection](wapahki-benchmarks.md) before writing. The facility record must connect an evidence-backed process to a proposed intervention baseline, the task denominator and plant guardrails. Recycling defaults to pilot outreach; new verticals default to discovery. A reusable adapter's promotion requires sourced observations and consistent semantics, and does not establish facility access or permission to control equipment.

Run from the repo with `.venv/bin/python skills/andrew-email-style/scripts/` followed by the helper:

- `outbound.py mission "plain-English goal"`: persist/resume the mission and policy. Chat/Codex executes research and lower-level steps; this parser does not independently browse.
- `outbound.py next CAMPAIGN`: actionable missing work.
- `outbound.py source CAMPAIGN captured-source.json`, then `account CAMPAIGN brief.json`: retain source quotes and fact IDs. Qualified briefs can proceed to writing; Maybe/No cannot.
- `outbound.py apollo-search CAMPAIGN ACCOUNT filters.json`: company-domain discovery. Verify current employer, rank roles before spending enrichment credits.
- `outbound.py apollo-enrich CAMPAIGN ACCOUNT PERSON`: only shortlisted people at qualified accounts; work email only, cached30days, no paid retry loop. Prefer protected local key file, then environment. Never print credentials.
- `outbound.py prepare CAMPAIGN ACCOUNT PERSON context.json`: compact research, selected sender context, current task seed and separate voice/outcome retrieval.
- `outbound.py rank-message CAMPAIGN ACCOUNT PERSON`: generate eight plain subject candidates, compatible body candidates and separate critics first; then select subject+body together. No fake Re/Fwd, hype, generic quick question or word-count mandate. Useful outcomes may break close ties; never optimize opens.
- `outbound.py recommend-time CAMPAIGN ACCOUNT PERSON`: recipient location → relevant office/facility → HQ, otherwise unknown. Personal location outranks HQ. UTC conversion uses IANA/zoneinfo, with optional timezonefinder geocoding. A recommendation is not a scheduled transmission.
- `operations.py score CAMPAIGN ACCOUNT assessments.json`: sourced ordinal score0–100, coverage and unknown dimensions, not calibrated probability.
- `operations.py opportunity CAMPAIGN ACCOUNT observed-opportunity.json`: actual reply/call/signature/payment/access evidence required. Do not record intended events as accomplished.
- `operations.py agreement CAMPAIGN ACCOUNT`: only after a sourced project is identified. Simple goal/work/deliverables/timeline/fee/payment/dependencies. No signature, invoice or funds transfer occurs. Currency explicit; signing payment must be funded before substantial work.

## Hiring and pressure signals

For Wapahki, follow [pilot LOI optimization](wapahki-loi.md). Use `operations.py pilot` to record observed qualification/owners/stages; positive conversations generate a local pilot brief. `pilot-metrics` measures qualified signed A LOIs and cycle times. A prepared brief, verbal interest, scheduled email, LOI signature and permission to use equipment are different states. Public research creates research-stage cases only.

Read the full JD, not just job counts. Hiring reveals possible skill demand and unfinished work; replacement versus expansion and outside-project budget remain unknown unless established. Contact the technical/workflow owner rather than automatically Recruiting. The posting usually stays out of the final email.

`signals.py watch CAMPAIGN ACCOUNT ats CAREERS_URL SOURCE_ID` uses the pinned MIT ats-jobs implementation, which normalizes12ATS providers. Retain raw provider responses, full normalized descriptions, published/updated/observed dates and version diffs. A researched company-to-board link is required; a guessed slug can belong to another company. On sources without descriptions, fetch and capture the full posting before classification. A first-seen date is not a posting date.

`signals.py classify-job SIGNAL_ID classification.json` requires actual JD quotes, problem/skills/team/likely owner and reasoned relevance. Distinguish inferred owner from a verified person. Its multiplicative signal score combines technical overlap, mission interest, active problem, boundedness, freshness and ability to pay. This influences priority only on already-qualified accounts. Unknown published dates receive limited freshness weight. It never generates an application or assumes a vacancy means budget for Andrew.

Use JobSpy only as broader discovery fallback: `.venv-jobs/bin/python skills/andrew-email-style/scripts/discover-jobs.py "planning simulation" --location Canada --output campaigns/MISSION/discovery/jobs.json`. It has a separate environment because its NumPy pin conflicts with timezonefinder. Verify discoveries at official sources before qualification. No proxy or CAPTCHA-bypass loop.

`signals.py watch ... rss URL SOURCE_ID` or `page URL SOURCE_ID` monitors researched company newsrooms/status pages, relevant regulators, public funding data and trade sources. `signals.py poll` captures changes; Codex triages them into `signals.py pressure ... pressure.json`.

Pressure types: regulation, funding, expansion, incident, hiring, target, news. Keep observed fact/metric/date/source/actual owner distinct from inference and proposed relevance. Event date and observation date are separate. Default `should_mention_in_email:false`. No generic congratulations opener.

For regulation, store jurisdiction, legal obligation owner and evidence of applicability before mentioning a duty to the recipient. Producer-responsibility targets do not automatically apply to each processor. Government funding or a capacity target can justify investigating equipment and operational ownership, but not claiming a failure, contractual budget or technical solution. A regional outage story does not prove a particular customer's devices were affected. Signals stack with fit; they never replace the product/data/automation gap gate.

## Implementation references

Patterns reviewed14Sept2026, not imported sending infrastructure: [OpenOutreach](https://github.com/eracle/OpenOutreach), [outreach-agent](https://github.com/Abhipaddy8/outreach-agent), [cold-cli](https://github.com/andersmyrmel/cold-cli), [sales-research-agent](https://github.com/aawais-ai/sales-research-agent). Mission decomposition, stored pending actions, source IDs and separate research/writing.

UI/data references: [Twenty](https://github.com/twentyhq/twenty), [Atomic CRM](https://github.com/marmelab/atomic-crm), [warpdrive](https://github.com/sneg55/warpdrive), [Vercel email-agent](https://github.com/vercel-labs/email-agent), [Denshees](https://github.com/Webeasetech/denshees). Shared objects, tables, account detail, timeline and progressive disclosure. This local implementation uses React, TanStack Table, accessible Radix dialog primitives and SQLite; it does not require their hosted services or import their senders.

Jobs: [ats-jobs](https://github.com/shunsukefuruyama/ats-jobs), [ATS API reference](https://github.com/ConorsCode/ats-api-reference), [JobSpy](https://github.com/speedyapply/JobSpy), [Job_Scraper](https://github.com/ScottCoffin/Job_Scraper). The unqualified name “crier” could not be resolved to the claimed watcher repository, so no code or claims from an unrelated project were imported.
