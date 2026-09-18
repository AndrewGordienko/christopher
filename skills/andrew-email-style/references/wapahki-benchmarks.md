# Wapahki pilot and benchmark selection

## Current cell gate (September 2026)

For new Morrow/Wapahki pilot outreach, [morrow-pilot-qualifier](../../morrow-pilot-qualifier/SKILL.md) and the other five linked stages in the main skill supersede older automation-only selection, plant-wide baseline offers and volume targets below. A scored QUALIFIED cell is required before writing; POSSIBLE means more research, HOLD means no outreach. Historic examples remain history. First scope: one cell, passive faults/actions/restored-state observation, repeatable human intervention time, then one separately authorized suitable recovery. Neither a robot installation nor downstream manual sorting proves recurring operator recovery. The UofT student identity is supported; a formal university research-project affiliation requires separate evidence.

Commercial progression follows [qualified pilot LOI optimization](wapahki-loi.md). The near-term north star is first contact → qualified signed pilot LOI; the benchmark remains the technical proof and customer-value foundation. LOI intent never substitutes for a definitive agreement, measured baseline or explicit access/control permission.

Wapahki's working thesis is to turn real deployments into reproducible recovery evaluations, then use those evaluations to compare and improve recovery policies. This is a product direction, not evidence that automatic benchmark construction or general recovery already works. Reuse the event model, metric definitions and evaluation protocol; adapt the task semantics and signal mapping. An “80/20” split is an architectural aspiration, not a measured integration cost.

The market is recovery/reliability software for deployed robots and automated cells. Recycling is the initial validation beachhead, not the definition of the company. Run two parallel engines: recycling pilot development and cross-vertical discovery. The expansion order is a hypothesis to test: recycling/tire recovery → food/packaging, warehouse/AMR and plastics/material processing → metal/machinery and general industrial cells → electronics, automotive and regulated production. Robot installation counts are market context, not a serviceable software revenue estimate, installed-base intervention rate or evidence of an accessible buyer. Keep industrial-robot and mobile/service-robot statistics separate.

Prove four things independently: recurring recovery need, consistent measurement, improved intervention burden with plant guardrails, and transfer with bounded adapter work. Track engineering hours to ingest signals, label events, configure success/guardrails and validate each adapter; record reused versus changed components, site-specific code, time to first valid baseline and subsequent maintenance. A new bespoke multiweek evaluation at each plant is evidence against easy transfer, even when the demonstrations succeed.

## Research four separate things

A facility is a prospective customer, not a source of training data. Before drafting, build `pilot_value_case`: facility identity; sourced public business objectives and unconfirmed KPI candidates; current pressure with owner/geography/date; deployed automation; explicitly labeled failure hypotheses; Wapahki metric; conditional economic/operational link; customer value proposition; and a lowest-risk first step. The chain must be credible from the actual process: failure → human recovery → active labour and/or lost productive time or degraded quality → customer KPI → useful operational outcome. Intervention does not necessarily cause line downtime, and reducing it does not necessarily increase throughput at a non-bottleneck. Never invent frequency, downtime, savings or a value of operator time.

Use `business_metric.primary:null` and `primary_candidate` when management's metric is unconfirmed. Process evidence may justify a candidate question, not a claim that management uses it. An initial conversation can establish the unknown baseline. If even the hypothesized chain is unsupported, research further or use discovery rather than automatically drafting.

After engagement, make the proposed value exchange explicit. Read-only observation should return a failure taxonomy, audited intervention baseline, coverage limits and analysis of productive time lost. Historical/offline work should return evaluated recommendations and a bounded estimate of potentially recoverable burden, with counterfactual uncertainty. Assisted recovery requires human confirmation; automatic recovery requires narrowly authorized classes and separate safety review. Deliver useful results before seeking wider access. These are proposed deliverables, not completed benefits or unconditional software-performance promises.

Separate site data, normalized event representations and model-improvement rights. A normalized or anonymized representation is not automatically unrestricted. Cross-site training, retention, sharing and derived-learning permissions are explicitly negotiated; they are not a prerequisite for a first meeting and are never implied by read-only access. Do not lead with model training, a dataset moat or helping Wapahki generalize.

Research geography at the facility level: province/country, actual obligation owner and applicability, grants, current commissioning/expansion, relevant integrators and realistic visit feasibility. Labour shortage/cost, funding eligibility and travel availability stay unknown without evidence. Ontario rules do not apply to Québec, Alberta or BC merely because all are Canadian. Keep this research behind the email unless one fact changes the operational reason to talk.

For every facility record `benchmark_hypothesis` in `research.json`, following the contract below. Rank the facility first and parent company second. Assess observable intervention burden and the feasibility of measuring it alongside automation intensity; do not use robot count or public capacity as proxies for data access.

1. **Existing production objective.** Preserve sourced throughput, quality, yield, recovery, purity, availability, cycle-time or other operational measures. Distinguish actual performance, design capacity, future targets and permitted intake. When the management KPI is unknown, say so and name proposed questions. Company or producer obligations do not become plant KPIs.
2. **Failure surface.** Identify where people plausibly diagnose, clear, reset, reconfigure or recover the process. Separate documented intervention from inferred jams, misfeeds, uncertain vision, variable material, failed grasps, blocked routes or downstream stops. Normal manual sorting, routine service and safety-required work are separate categories, not automatically recoverable failures.
3. **Recovery benchmark.** Propose an intervention-burden metric and a denominator appropriate to the specific process: pick, cycle, mission, tonne, case, batch, retread or hour. Record how it could be observed and what is missing. A proposal is not a baseline result.
4. **Plant guardrails.** Propose relevant task success, throughput, quality, purity, yield, cycle-time and safety measures. Confirm definitions and acceptable change with the operator before testing. Reduced intervention is not improvement if output deteriorates or risk increases.

## Shared event model and measurement contract

`normal operation → failure begins → detection → recovery attempt → recovered/not recovered → stable operation → downstream task outcome`

Retain asset/line, event and parent-incident IDs; source clocks and synchronization uncertainty; task/lot/material context; fault class and severity; detector, policy and adapter versions; attempt actor (human/software/assisted); attempt start/end; outcomes; stability window; downstream QC; provenance and missingness. Faults can overlap and recovery can involve repeated attempts. Missing timestamps remain unknown. A reset acknowledgement alone is not stable recovery. A safety stop is an event to understand, not permission to clear it.

Metric definitions are shared; mappings and thresholds belong in a versioned adapter:

- **Human intervention minutes per operating hour:** propose summed active person-minutes spent diagnosing and recovering, divided by a predeclared observed production-exposure window in hours. Count concurrent workers as person-minutes; this rate can exceed 60. Keep waiting time separately. For the initial baseline, include unplanned recovery stops in exposure and disclose planned exclusions and missing coverage; also report actual run-hours so stopping the machine cannot make the rate look better. Agree the plant's convention before adopting its label “operating hour.”
- **Recovery-attributable downtime minutes per exposure hour:** union of affected-line stopped intervals attributable to recovery; do not sum overlapping alarms or conflate downtime with hands-on labour.
- **Intervention events per production unit:** deduplicate incident-linked interventions; retain all alarm/attempt records. Report both absolute counts and the exact exposure denominator. A pick denominator means all attempts, not only successful picks. Tonnes require a defined stream and mass boundary, not repeated counting of recirculated material.
- **Time to stable recovery:** failure-onset to sustained acceptable operation, plus detection delay, waiting and active attempt time separately. Report median and tail behaviour when estimable, including unrecovered/right-censored episodes; do not drop hard cases.
- **Autonomous recovery rate:** only for a separately authorized intervention phase. Successful software-only recovery with sustained task success divided by all prospectively eligible failures, including abstentions and failed attempts. Also report coverage of all failures and success per attempt. Do not infer it from historical human recoveries or label offline predictions as actual autonomous recoveries.
- **Task success and intervention-free operating time:** retain exposure, failed tasks, aborts and censored windows. Reduced logging or suppressed interventions is not improved reliability.

The adapter defines task unit, success predicate, production denominator, normal manual work, eligible failure types, safety limits, stability window, business guardrails and signal-to-event mapping. Sensor accuracy, event-detector precision/recall, human label agreement and missingness must be assessed; a shared schema alone does not make evaluations comparable.

## Two outreach modes

**Pilot mode, currently recycling.** Variable inputs are a reason to investigate a potentially rich failure distribution, not proof of frequent failures at every plant. Initial progression is remote technical call → remote workflow/technical scoping (optional later visit) → agree baseline and telemetry scope → authorized read-only collection → reproducible baseline → offline evaluation → separately authorized assisted recovery → separately authorized controlled recovery. A shortlist verdict of Yes means worth a conversation, not deployed, access-granted or pilot-ready.

The observational milestone is an audited event dataset, explicit metric definitions, coverage/uncertainty and a reproducible baseline. Establish relevance and trust before asking for raw telemetry. Prioritize sites where interventions, production exposure and downstream outcomes can plausibly be linked in time. Actual retention, ownership and export permission must be established.

**Discovery mode, new verticals.** Learn what constitutes failure, what people do, what is logged, what management measures, which denominator makes sense, whether frequency warrants work, and what safety constraints apply. Leave unresolved units and metrics null rather than copying tonnes or OEE into aerospace, food, pharma, warehouses or other sectors.

Promotion to a vertical `pilot_ready` adapter needs a consistent pattern at **at least three distinct companies**, supported by sourced conversations/observations. Resolve who feels the pain, who signs, available telemetry, common failure taxonomy, success metric, denominator, safe bounded recovery actions and a plausible 4–8 week pilot scope. Store answers with evidence, consistent task/recovery semantics, a documented signal mapping and outcome check, plus disagreements and remaining integration work. Three companies is a screening floor, not sufficient scientific validation. Never promote because a fixed number of emails was sent, elapsed time passed, or public research mentioned automation. Vertical readiness does not grant access at any facility.

Track facility progress as `researched → contacted → conversation → visit → baseline → data_access → offline_eval → shadow_mode → assisted_recovery → closed_loop`. At `baseline`, agree definitions and collect an initial remote or site observation if available; a reproducible telemetry baseline may require the later data-access step. Record accomplished stages with evidence; a planned visit is not an observed visit, and a proposed baseline is not measured. Shadow mode only logs recommendations and has no command authority. Advancement to assistance or closed loop requires its own facility-approved scope, safety process and evidence.

## Comparable policy evaluation

Compare policies only where their observation/action interface and task are compatible. Version and hold fixed the task, starting-state distribution, failure/perturbation distribution, eligibility criteria, success/stability criteria, safety constraints, time/compute/episode budgets, reset procedure and production guardrails. Log adaptation/training budgets as well as inference performance. π0, OpenVLA, an OEM policy or a Wapahki recovery policy is a candidate, not automatically interchangeable hardware software.

Hold out failure episodes and relevant time blocks, lots, sites or failure families to avoid leakage. Separate training, tuning and final tests; freeze the evaluation set or version changes. Report results by failure/severity/material strata and on normal operation so false interventions are visible. Use representative sampling plus explicit stress sets; never quietly replace real exposure with a hand-picked easy set.

Before/after production comparisons are vulnerable to material mix, staffing, maintenance, shift and equipment changes. Prefer matched or randomized blocks where feasible; record confounders and use uncertainty appropriate to repeated events within shifts/sites. Predefine the practical improvement and non-inferiority margins and plan exposure accordingly. “No statistically significant degradation” is not evidence of equivalence. With insufficient data, say inconclusive. Zero observed safety violations is not proof of safety.

Offline replay can evaluate detection, labeling and recommendation agreement. Unexecuted actions usually lack counterfactual outcomes; simulation needs its own fidelity validation. Report these as offline/simulation evidence, not causal reductions in live human intervention or general robotics capability. Cross-task claims require held-out task/site evaluations and disclosed adapter work.

## Stored contract and writer boundary

`benchmark_hypothesis` has `schema_version:1`, `status:proposed`, `mode:pilot|discovery`, `vertical`, `adapter_id`, `adapter_status:hypothesis|pilot_ready`, `basis:[fact_ids]`, `existing_production_objective`, `production_unit`, `task_success`, `primary_wapahki_metric`, `secondary`, `plant_guardrails`, `likely_failure_classes`, `data_sources`, `baseline_plan`, `readiness`, `outreach_question` and optional `promotion`.

Alongside it, store `pilot_value_case` with `status:hypothesis`, `basis:[fact_ids]`, `business_metric:{primary,primary_candidate,secondary,status,evidence}`, `current_pressure`, `automation`, `failure_hypotheses`, `wapahki_metric`, `economic_link:{hypothesis,chain,basis}`, `pilot_value_proposition`, `first_step`, `value_exchange`, `geography` and `data_rights`. The writer gets only the compact operational question and conditional customer value, not a raw research/telemetry inventory. Confirmed business metrics require facility evidence; missing figures remain null.

- `existing_production_objective`: `status:unconfirmed|confirmed`, `public_measures:[{kind,description,basis}]`, `candidate_metrics`, `confirmed_kpis:[{metric,basis}]`. Kind distinguishes `design_capacity`, `target`, `reported_performance`, `permit_limit`, `process_quality`, `investment`, `access_signal`, `unknown`. Only direct facility evidence can support confirmed KPIs; qualification remains a semantic research judgment.
- `production_unit`: `{type:null|string,status:proposed|confirmed|unknown,definition,basis}`; `task_success`: proposed or confirmed success predicate. In discovery, null and a precise question are useful.
- `primary_wapahki_metric`: `{id:null|string,status:proposed|unknown,definition,unit,phase:observational_baseline}`. `secondary` includes `phase` so later recovery metrics cannot masquerade as baseline measurements.
- `plant_guardrails`: `[{metric,status:proposed|confirmed,basis,acceptance_margin:null|...}]`. Set margins with the operator; do not invent tolerances.
- `likely_failure_classes`: `[{class,status:hypothesis|documented,basis}]`. `data_sources`: proposed records, event mapping, availability and clock/coverage unknowns. No assumed access.
- `baseline_plan`: `{event_model_version:recovery-v1,exposure_definition,intervention_definition,downtime_definition,stability_criterion,comparison_plan,unknowns}`. It is a protocol proposal; `readiness` records actual access/baseline/permission evidence separately.
- `promotion`: independent `{observation_id,company_id,facility_id,kind:conversation|site_observation|telemetry_review,basis}` records plus `consistent_pattern`, `adapter_complete`, `contradictions_resolved`, a rationale and `answers` for `pain_owner`, `buyer`, `telemetry`, `failure_taxonomy`, `success_metric`, `denominator`, `safe_recovery_actions`, `pilot_scope`, each `{answer,basis}`. Public marketing facts alone do not qualify.

`research.py` validates and passes a compact `benchmark_context` to the writer; `mission.py next` flags missing benchmark research. The full metric framework belongs in research/account views. First touch asks the operational question, with at most one or two useful facility facts:

“I’m building Wapahki around reducing the time people spend recovering automated systems when something goes wrong. … I’m curious how you measure those interruptions and the time it takes to get the line running again.”

Adapt that thought to the actual process and recipient. Do not dump a KPI list, request control or raw data at first contact, invent downtime, or promise a reduction. Preserve the existing useful subject and task-specific wording. Any revised unsent email must go through the normal critic and approval invalidation workflow; preserve actual sent history and company-wide reply pauses.

Match recipient altitude while preserving the same thought: controls/maintenance gets what stops and how it is recovered; plant operations gets productive time lost clearing/resetting/restarting; corporate engineering gets whether a useful approach could transfer, beginning with one facility and its measured intervention burden. Andrew's current UofT student identity can be used when supplied as current context. Generality is a question for research, not a first-touch capability claim. Make a concrete conditional baseline/recovery-software offer and ask for a short remote technical call. Do not make a visit the CTA.

## Primary research checked 14 September 2026

These sources support the measurement direction, not Wapahki product validation:

- [ISO 22400-1](https://www.iso.org/standard/56847.html) provides a framework for manufacturing KPIs across production types. Its catalogue says the 2014 edition was confirmed in 2025; this does not establish any prospect's adopted KPI.
- [Berkeley AutoEval](https://arxiv.org/abs/2503.24278) studies automated real-world evaluation using success detection and scene resets. It was submitted in March 2025.
- [ARMADA](https://arxiv.org/abs/2510.02298) reports both task success and intervention-rate results on four tasks. Those results do not transfer to recycling plants without evaluation.
- [Eval-Actions](https://arxiv.org/abs/2601.18723) evaluates execution quality beyond binary task success. Its current title differs from an older search listing; do not confuse its AutoEval evaluator with Berkeley's project.

The unspecified “2026 audit” in the strategy discussion has not been identified with confidence. Do not cite it as verified. Keep illustrative before/after numbers out of actual pilot records.
