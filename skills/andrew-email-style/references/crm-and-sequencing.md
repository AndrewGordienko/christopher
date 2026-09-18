# Outbound CRM and follow-up engine

Maintain the relationship, not just the draft. At any time, persisted state should explain what happened, who is waiting on whom, what Andrew should do next, which accounts are progressing, and what deserves tomorrow's capacity.

SQLite is authoritative for local state. Gmail supplies observed messages and scheduled-send state; Apollo supplies sourced person/contact data. An app state cannot make a Gmail cancellation or delivery true. Research and draft artifacts support the database and retain provenance.

## Object contract

Maintain Workspace, Mission, Account, Facility, Person, Thread, EmailTouch, ResearchSignal, Source, ScheduledSend, Task, Opportunity, Meeting, Outcome and Suppression. Link every message/touch to workspace, mission, account, person, objective, sender, thread and touch number. A first-touch draft may have a local conversation key before Gmail assigns a thread ID; do not fabricate a Gmail ID.

Account state includes fit/priority, stage/status, primary/backup contacts, first/last contact and reply timestamps, next action, active-thread/useful-reply/meeting counts, opportunity value/probability when supported, research freshness and suppression reason. Account-level restrictions outrank individual eligibility.

Person state includes role/function/seniority, email and verification evidence, Apollo ID, location/timezone evidence, rank/score, relationship state, contact/reply/next-action timestamps and suppression. Rank #1/#2/#3; never activate all three together.

Thread state includes local/Gmail IDs, subject, sender/recipient, first/last outbound/inbound, reply state/outcome, next action and status. A touch stores initial/follow-up/reply type, actual subject/body, scheduled/sent/delivered timestamps with observation or explicit user-report provenance, timezone, research/writer versions and attributed outcome. Preserve prior versions and evidence for every transition. A user report of sending does not establish delivery.

## Recording an email Andrew sent himself

The CRM's **Mark as sent** action records the exact displayed message and Andrew's reported send time. It does not send mail. Store an immutable receipt with the subject/body hash, sender, recipient, touch, reported send time, recording time and explicit user-action source.

Mark that contact sent and the account contacted, retain advanced relationship stages, and set a follow-up eligibility date when awaiting a reply. Do not create another first touch for the same email. Retries are idempotent, and a later Gmail observation must not double-count the touch. Keep user-reported and Gmail-verified evidence distinguishable; never fabricate Gmail message/thread IDs.

If Gmail already has a schedule record, flag it for reconciliation. Recording a manual send does not prove the remote scheduled message was cancelled or delivered. Do not mutate historical subject/body or execution receipts to make them match the new report.

## Next-action invariant

Every active relationship has a dated next action, an open task requiring Andrew, a pending reviewed action, or an explicit paused/terminal disposition. A temporary pause has a reconsideration date; an indefinite manual hold remains visible with its reason. Never manufacture a meeting, expected payment or deadline to fill a field.

After a send, reply, meeting or decision, set the next action or deliberately close/pause. Flag an active relationship or opportunity with neither as orphaned. Replies requiring Andrew and meeting/opportunity steps come before blocking problems, due follow-ups and new first touches.

## Outcomes and suppression

Classify incoming messages with supporting Gmail message evidence: positive_interest, technical_answer, routing, meeting_proposed, meeting_confirmed, next_step, question, neutral_reply, deferment, decline, not_relevant, out_of_office, bounce, unsubscribe, automated_reply or reply_attribution_uncertain. Existing storage aliases such as `positive`, `declined`, `automatic` and `unknown` must not change their meaning.

Useful responses are routing, technical answers, positive interest, meetings and concrete next steps. Keep raw human replies separate. A reply does not prove interest, a proposed meeting does not prove booking, and a booking does not prove attendance.

Any genuine human reply stops no-response follow-ups. Meaningful account replies also pause alternate contacts until reassessed. Unknown attribution pauses for review, never silently promotes an opportunity. Explicit opt-outs, invalid addresses and manual/legal suppression stop outreach. A live conversation elsewhere at the account blocks a fresh cold sequence.

OOO is not a human-response success. Defer until a sensible date after return and cancel sends during absence. An alternate person in an OOO is a lead to evaluate, not automatic permission to contact. Without a return date, set a conservative recheck rather than declaring the person unresponsive.

Declines normally close the sequence. Store timing/no_budget/no_need/wrong_person/no_external_contractors/existing_solution/not_interested/other only when supported. A deferment may create a later task. A bounce suppresses the address; re-resolve the person if worthwhile without automatically advancing to contact #2.

## Account-level sequencing

D0 initial; D3–4, D8–10 and optional D15–18 are eligibility windows, not automatic sends. At eligibility: sync mailbox, read the complete thread, check the account, refresh relevant research, then choose:

- FOLLOW_UP_SAME_PERSON: clarify, narrow, add a technical thought/result, respond to new work or ask about ownership.
- CONTACT_NEXT_PERSON: only after explicitly deciding this person is a better path than following up. Hold the other path.
- WAIT: a reason and future reconsideration date.
- COMPLETE: deliberate closure.

The existing CLI calls drafting decisions SEND/WAIT/COMPLETE; a next-contact move must be persisted as an explicit account choice, never simulated by independently scheduling a backup. Refresh checks if anything changes. Do not prewrite an entire sequence on Day 0.

No “just following up”, bumping, repeated biography or recycled pitch. Keep the same thread, sender and subject for normal follow-ups. A materially new reason much later may warrant a new conversation after review.

## Opportunities

Contract: conversation → project identified → scope discussed → agreement sent → signed → paid → delivering → complete. Store project hypothesis, actual scope, estimated/quoted values, currency, decision maker, expected close date, agreement/payment state and next action. Unknown value/probability remains unknown.

Wapahki: conversation → site visit → data discussion → data access → pilot → recovery testing → deployment → customer. Track access/data/pilot progress separately from revenue.

OutageHub: product fit → conversation → API evaluation → commercial discussion → integration → customer.

An opportunity requires evidence of an actual conversation/next step. Drafting a scope is not agreement, a signature is not payment, and a payment promise is not cash received. Do not create these states from positive wording alone.

## Nightly operating loop

Sync Gmail/Apollo and scheduled sends → classify new evidence → update relationship/task state → cancel invalid sends → refresh due research → choose same person/next person/wait/complete → rank actions → fill up to capacity → draft selected actions → fact/voice/recipient/attachment/timezone/account/batch checks → Andrew's review queue.

Use [nightly-workflow.md](nightly-workflow.md) for the actual CLI and access limitations. Prioritize replies and active relationships before more cold drafting. Rank fit, real societal/strategic value, signal freshness, recipient ownership and comparable useful progression. Prepare fewer than capacity rather than fill with weak prospects. Do not claim trained response probabilities from heuristic scores.

Use [scheduling and batch review](scheduling-and-batch-review.md) for recipient-local windows, spacing and pre-approval checks. A scheduled message becomes invalid when a reply, meeting, pause, suppression or stale fact changes the account. Native Gmail scheduling requires an actual cancellation; document unavailable watchers/access honestly.

## Operational views

Today: replies needing Andrew, meetings/opportunity steps, blocking problems, then review queue. Account: overview, people, emails, research, opportunity, sources, with one evidence-backed chronological activity timeline. Workspace pipelines share the same accounts/people/threads and change their stages rather than creating separate apps.

Keep [the fixed Gmail labels](gmail-labels.md) reconciled: exactly one workspace and one applicable primary status, with temporary action labels. Never create company/person labels or remove unrelated labels. Labels are a recoverable operational view.

Analytics use actual sent counts, human/useful replies, meetings, opportunities and conversions. Compare useful replies/sends, meetings/sends, opportunities/contacted accounts, conversions/opportunities and revenue/contacted accounts. Slice when data supports it by workspace/mission, role/seniority/rank, industry/company size, subject pattern, touch, local day/hour, problem/impact category and signal. Wapahki emphasizes visits/data/pilots; OutageHub evaluations/integrations; Contract signed/paid work and impact category. No open-rate optimization or invented denominators.

Compare accumulated internal results before replacing priors about timing, contact seniority, follow-up delays, project specificity or moving contacts. Preserve sample size, censoring and confounders; association is not causation.

## Implementation honesty

Use the existing state, operations, execution, labels, signals and opportunity modules. This reference defines the operating contract; it does not certify that every UI view, object or autonomous integration has been built. Inspect real persisted state and available tools before claiming a capability or completed sync. Keep missing integration coverage and orphaned relationships visible.
