# Wapahki: qualified pilot LOIs

## Current cell gate (September 2026)

For new Morrow/Wapahki pilot outreach, [morrow-pilot-qualifier](../../morrow-pilot-qualifier/SKILL.md) and the other five linked stages in the main skill supersede older automation-only selection, plant-wide baseline offers and volume targets below. A scored QUALIFIED cell is required before writing; POSSIBLE means more research, HOLD means no outreach. Historic examples remain history. First scope: one cell, passive faults/actions/restored-state observation, repeatable human intervention time, then one separately authorized suitable recovery. Neither a robot installation nor downstream manual sorting proves recurring operator recovery. The UofT student identity is supported; a formal university research-project affiliation requires separate evidence.

The near-term commercial objective is to minimize elapsed time from first contact to a **qualified signed pilot LOI**, without lowering scope quality or hiding slow/open opportunities. The product objective remains measurable recovery improvement. Recycling is the first beachhead for a reusable recovery/evaluation framework.

## Relationship progression

Research → Contacted → Conversation → Qualified → Site Visit → Pilot Scoped → LOI Sent → LOI Negotiating → LOI Signed → Data/Security → Pilot Agreement → Baseline → Offline Evaluation → Assisted Recovery → Closed-Loop Recovery → Commercial Deployment.

These are observed milestones, not compulsory meetings. Scope remotely when sufficient; accelerate with a ready customer. A definitive pilot agreement can supersede an LOI without fabricating an intervening LOI signature. Pause/close explicitly when there is no useful next action. Site access or limited confidential discussions may require confidentiality/security arrangements earlier than the illustrative funnel.

First touch offers a plausible operating improvement and asks whether the problem warrants a short remote technical call. A site visit is optional later; it is not required for an LOI. Do not ask for an LOI, proprietary data or control cold. Communicate the customer-value hypothesis: quantify productive time lost to human recovery, prioritize recurring cases, then evaluate whether software can reduce it within plant guardrails. Do not imply that operator effort always stops the whole line.

## Qualify the first useful conversation

Use a 20–30 minute call when useful, not a fixed meeting requirement. Establish:

1. The exact facility and automated line/cell/process.
2. What fails and the human intervention it requires.
3. How often it happens and how long recovery takes; unknown numerical baselines are acceptable.
4. What a person actually does, and what counts as stable production again.
5. Which customer KPI is affected and how the customer knows.
6. What events are logged and who owns the records.
7. The internal technical champion and practical line owner.
8. Who can authorize site access, data access, a pilot and eventual control, separately.
9. A technically credible, bounded recovery/evaluation approach.
10. What would prevent a pilot if a useful reduction could be measured: procurement, budget, security, safety, equipment-OEM or integrator constraints.

Do not infer authority from title or company size. Track `technical_champion`, `economic_buyer`, `pilot_signatory`, `security_owner` and `data_owner` as unknown until evidenced. The same person can fill several roles if confirmed. Research candidates separately. Select contacts for both technical ownership and a plausible route to authority; retain one active company contact. A reply pauses the company sequence, but creates an owned relationship next action rather than freezing the opportunity.

Before recommending an LOI ask, confirm facility, system, credible failure/recovery problem, actual human intervention, affected customer metric, plausible approach, technical owner and authorization path. Unknown event counts, downtime and savings must remain unknown. A public equipment page is not confirmation of intervention frequency or customer pain.

## After a positive call or visit

Record the observed conversation and evidence; update qualification and owners; identify remaining gaps; decide whether a visit/additional meeting is actually necessary; prepare the pilot hypothesis and a concise pilot brief immediately. A provisional brief can expose unknowns, but is not an agreed scope. Recommend the LOI ask only when the qualification threshold is met. Every active case has an Andrew-side owner, a specific next action and a due date or an explicit external trigger.

The pilot brief covers the exact system and problem, customer value, intervention events/minutes/recovery-time/production denominator, output and safety guardrails, proposed phases, facility and Wapahki contributions, indicative timing and unresolved conditions. It offers baseline/loss analysis, taxonomy, benchmark and evaluation/prototype. It does not silently promise a free pilot, savings, production access or deployable autonomy. Ask after alignment: “If this captures what we discussed, I’d like to put a short LOI in place so we’re both aligned on the pilot while we work through the technical details.” Drafting is local; sending still requires authorization.

## LOI quality and rights

Report document quality and execution separately:

- **A:** named company/facility and system, failure/recovery problem, customer metric and pilot objective, initial benchmark, both parties’ intended contributions (including technical contact and conditional access path), phased pilot path, indicative timing, commercial intent and explicit binding/non-binding treatment.
- **B:** named facility and intended pilot, with incomplete technical/commercial scope.
- **C:** generic willingness to explore.

Only an executed A document plus the qualification gate counts as a qualified signed pilot LOI. B/C signatures remain separately reported. Verbal interest, a draft, a signature request and an unsigned “agreed” document are not signed LOIs. Retain the actual executed document/capture, signature evidence, signatories and authority basis; record the signature date. A signature does not itself grant data or control access.

The standard legal form belongs with counsel. Record intended non-binding scope and any explicitly binding exceptions; do not infer enforceability from the document title. Keep site data, permitted evaluation use, normalized representations and cross-deployment model-improvement rights separate. No blanket/perpetual training right is a cold-outreach prerequisite. Confidentiality, security and data-use terms must be acceptable before proprietary data exchange. The definitive agreement resolves IP, pricing, responsibilities, acceptance, permissions and any derived-learning rights.

Cooley recommends early term sheets to capture key commercial expectations and notes that parts may be binding; its discussion is general guidance, not a Canadian pilot form. [Commercial contracts](https://www.cooleygo.com/six-things-startups-need-to-know-about-commercial-contracts/). Cooley also discusses specifying confidential information and permitted use. [NDA guidance](https://www.cooleygo.com/what-you-need-to-know-about-the-nda/). Checked 14 September 2026.

## Prioritize without invented probabilities

Track eight evidence-backed 0–5 ordinal dimensions: pilot fit, failure frequency, customer value, data accessibility, technical-champion access, signatory accessibility, safety/deployment ease and speed to LOI. Store unknowns as null, especially frequency, local signing authority and procurement duration. Public machinery evidence cannot fill those fields. A multiplicative index is available only when all eight are assessed; it is not a calibrated LOI probability. Show evidence coverage and the weakest/unknown factors alongside existing facility pilot/data rank. After qualification, prioritize strong customer value with a reachable champion and confirmed authority path, using close speed as a tie-breaker. Do not rank a regional plant as “can sign next Tuesday” merely because it is small.

## Measurement

Use actual first outbound timestamps and evidence-backed milestone dates. Local recommendations, Gmail scheduling and prepared drafts do not start the contact clock. Track median days for contact → qualified conversation, conversation → pilot scope, scope → LOI sent, LOI sent → signed A LOI, and contact → qualified signed A LOI. Report completed sample size, open count and open age with each median; zero observations means unavailable, not zero days. Do not reward only measuring fast winners.

Report signed A/B/C documents separately, qualified A LOIs / qualified opportunities, qualified A LOIs / facilities contacted, qualified A LOI → live pilot and live pilot → paid deployment. Keep numerators in the denominator cohort, report the cohort window/as-of date and pending/censored cases, and do not count an LOI as a live pilot or commercial intent as paid revenue. A measured result needs a captured evaluation outcome; paid deployment needs payment evidence.

## Local workflow

`operations.py pilot CAMPAIGN ACCOUNT observed-case.json` validates and records a case in SQLite, then exports `pilot-opportunity.json`; a positive conversation generates `pilot-brief.md` locally. `operations.py pilot-brief CAMPAIGN ACCOUNT` regenerates the brief from the case. `operations.py pilot-metrics` reports observed milestones. `mission.py` projects cases into the app and surfaces post-conversation qualification/brief/LOI next actions. Public research seeds research-stage cases only; nothing is contacted, qualified, signed or authorized by importing research.
