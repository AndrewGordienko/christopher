# Sender context

When Andrew's current location is London in the United Kingdom, write **London, UK** in future letters. Do not reuse the location when it is no longer current.

Andrew does not introduce himself the same way in every email. Before strategy and retrieval, determine:

1. What is he trying to accomplish?
2. Which project or company is this about?
3. Why is he personally credible to this recipient?
4. Which one to three current facts explain that?
5. Which facts should stay out?

Recipient context identifies their responsibility; sender context identifies which parts of Andrew are relevant. Voice remains Andrew's. These modes are selection guidance, not reusable biographies or automatic introductions. A strong task draft still leads. A scheduling reply normally needs no introduction at all.

## Contract and technical project outreach

Mode: `technical_contract`. Relevant facts may include UofT, current co-op/technical work, the concrete mechanism Andrew builds, relevant ML/RL/planning/simulation experience and why he wants to apply it to this problem. Use only facts supported by the current context.

The current Contract Work batch uses the [exact opening in the Contract style reference](contract-useful-work.md#opening), including the commas in “London, UK, working.” It retains the useful mechanism without an implementation inventory. These location/employer/stage facts belong to this task, not a permanent biography.

The Contract first-touch ask follows the [current small-contract wording](contract-useful-work.md#exploratory-ask) and develops from the preceding technical question. Do not introduce Wapahki unless relevant. `technical_work` is the adjacent general technical/research mode when the objective is not a contract; research collaboration or an existing team problem may fit that mode. Do not relabel historical internships as contracts.

### Individual-first outreach

For exploratory contract outreach, default to Andrew speaking as an individual. Lead with his own background, interest in the problem and the project he could take ownership of. Do not introduce a team merely because one exists.

A first email should feel like a capable person asking whether there is an interesting problem to work on. Do not turn it into a services company pitching capacity or add a team-size claim to establish credibility.

Prefer:

> I was wondering if there might be a project I could take ownership of.

Over:

> We're a four-person technical team available for contract work.

Ownership is not a promise to execute every part alone. If the recipient expresses interest and the scope would benefit from more people, Andrew can explain the collaborators he actually has and how they could help. For example, when supported by current context:

> I can take ownership of this, and if it makes sense to move faster or cover more ground, I also have a few people I work with who can help on the build.

Do not invent collaborators, their availability, credentials or a team size. Do not imply Andrew is the sole executor when the agreed scope requires a team, and answer a direct question about who will do the work honestly. Relevant team involvement should be clear when scope and responsibilities are agreed.

This is a default for exploratory contract outreach, not a universal ban on "we". Andrew's current instruction, the actual thread and an explicitly team-led project can require a different introduction. Keep Wapahki founder/team and OutageHub company contexts distinct.

## Wapahki pilots and customers

Mode: `wapahki_pilot`. Relevant current facts may include Andrew's UofT/AI/robotics founder or team context, a recovery layer for deployed robotic cells, prototype/recovery-algorithm work and the practical first step sought.

A personal introduction can explain a robotics company working on recovery when cells encounter situations they were not programmed for. A team introduction can describe the AI/robotics engineers building it. Choose the frame that fits the relationship and supplied draft.

Fundraising belongs only when currently true and useful. Do not automatically add "raising a pre-seed" or lead a factory email with it. Keep the operational problem central: robots stop and people need to step in. Do not invent pilots, deployments or traction.

## Wapahki investors

Mode: `wapahki_investor`. Frame Andrew as the founder: what Wapahki is solving, concrete progress since the last exchange, prototype/factory/integrator/customer learning, and financing context when relevant.

UofT and technical work can support that background; do not turn a financing conversation into a student seeking advice. Reply to the current thread before adding an update. Do not force a biography into scheduling.

## Factory and integrator learning

Mode: `factory_learning`. If the objective is learning, useful current context may be UofT, robotics/AI work and trying to understand real factory automation, where cells fail and where people intervene.

Preserve a learning visit. Do not introduce a pilot, deployment, customer relationship or data partnership unless that is the actual objective. Naming Wapahki in the context does not automatically make a visit a pilot.

## OutageHub

Modes: `outagehub`, `outagehub_acquisition`, `outagehub_api`. Use Andrew's relevant OutageHub role and current product/company facts. Leave out UofT, robotics and Wapahki unless specifically relevant.

In acquisition discussions, write as an owner/operator discussing the business and answer the transaction question directly. In API sales, discuss outage data, coverage, reliability and the buyer's use case. Do not transfer old valuations, pricing, coverage or acquisition terms into a new thread.

## Warm personal relationships

Mode: `warm_personal`. Former coaches, teachers, mentors and friends rarely need a credibility paragraph. Use shared history where relevant. Do not convert a reconnection into a founder pitch. A commercial warm introduction alone does not make a message personal.

## Execution contract

Codex resolves `objective`, `project` (Andrew's project, not the recipient company), `recipient`, `relationship` and optional explicit `sender_mode`. The local `select_sender_context` router handles known objective/project combinations; unknowns stay unknown. Do not fabricate certainty to fill a mode.

Select up to three relevant entries from `current_facts` using `sender_fact_indices`. The helper copies only those entries into `sender_context.identity`, preserving their indices as provenance. Those raw facts are evidence, not prose to paste verbatim. Before drafting, apply [human-compression.md](human-compression.md) to choose their simplest useful expression for this recipient. The helper does not independently verify facts or generate a biography; Codex checks truth, freshness and relevance.

`prepare` runs sender selection before Sent retrieval and includes the result in the writer packet. History can match on `sender_mode` alongside relationship/objective, but never replaces the task draft or supplies stale identity facts. The critic must affirm `sender_context_fit` before ranking: right role, relevant facts, no unrelated company or unsupported status.
