# Scheduling and batch realism

Resolve each recipient's IANA timezone from verified work location, relevant office/facility, company headquarters, then an explicit Apollo timezone. Keep the evidence and fallback level. Unknown or ambiguous means hold; Andrew's timezone is not a fallback. Display recipient-local dates and times first. The Gmail picker timezone is only a conversion step.

Default cold first touches to weekdays, roughly 08:30–11:30 recipient local time. These are configurable priors, not proven optimum hours or minutes. A current instruction can permit an afternoon window. Let actual comparable useful replies inform later changes. If no eligible slot remains, wait for the next window rather than compressing the queue.

Give every recipient an eligible local window, distribute messages through it, vary spacing and respect mailbox/day/hour capacity. Higher-ranked accounts get capacity first. Leave gaps when there is nothing worth sending. Do not schedule everybody at 09:00, use an exact five/ten-minute sequence, or cluster one timezone into a burst. A round minute is not itself an error; a repeated mechanical pattern is. Do not add meaningless randomness or claim irregular timestamps improve replies or conceal automation.

Never schedule several people at an account at once. Contact #1 goes first; #2/#3 stay held. A later decision chooses a follow-up OR another contact. A human reply pauses the whole account.

Immediately before scheduling, refresh account/thread history and check replies, meetings, opt-outs, bounces, manual pauses and stale information. Cancel invalid pending sends. Recheck during mailbox sync and before delivery when execution access is available. Gmail's native scheduler does not call our local checks at delivery time: local suppression is not cancellation until the actual Gmail scheduled message is cancelled and verified. Do not claim unattended protection without a functioning watcher.

# Batch anti-AI-smell check

Review the collection before it becomes eligible for approval. Good individual emails can still expose a noun-swapped campaign template.

Stable current facts about Andrew may repeat verbatim. Use “London, UK”. Do not paraphrase a true biography to create artificial variation. Shared core wording across people at the same organization can also be appropriate.

Inspect repetition outside biography and sign-off: “seemed like a good fit”, “I've been looking for ways to use that skillset”, “One thought was”, “I was wondering if there might be”, “but I'd much rather work on whatever problem”, identical call requests, paragraph rhythms and subject grammar. Frequency is a flag for a semantic critic, not an automatic ban.

Ask what Andrew actually wants to say about each organization. Fix the thought when it is generic. Never repair repetition by thesaurus substitution, changing good prose or inventing different angles.

Research determines selection, recipient, problem, timing and possible work. Include a fact only if it makes the reason for writing clearer. No funding congratulations or research recital for its own sake.

Do not manufacture moral justification. Prefer the real consequence, such as earlier wildfire detection, less water loss or more reliable transit. If the technical reason already explains why the work matters, it does not need another impact sentence.

Do not force every organization into a simulation/evaluation harness. Keep a benchmark, failure search, planning prototype, sensitivity analysis, data analysis, implementation or investigation when that is the actual useful idea. Asking what the team has not had time to own is valid too. Do not invent scope merely to diversify a batch.

Likewise, no universal CTA. Use the natural next step for this email: a call, interest in a project, a technical question or a pointer. An identical appropriate ending is not by itself a reason to rewrite.

Subjects should be plain, concrete and independently plausible. Avoid repeated student/skills pitches, hype, fake Re:/Fwd:, or a batch all using “Possible project” or “[noun] project”. Preserve Andrew's explicitly selected subject unless current instructions change it.

## Campaign-level critic

Read five or more emails side by side, then inspect the entire batch:

1. Which repeated phrase is unjustified outside genuine boilerplate?
2. Do subject grammar, motivations, proposed work or endings expose the same template?
3. Are projects different in substance or just renamed harnesses?
4. Are times mechanically regular or clustered?
5. Is more than one person at a company eligible?
6. Has any evidence, mailbox state or approved wording become stale?

The deterministic lint in `scripts/campaign_lint.py` finds candidates for this review. It cannot judge Andrew's voice or verify freshness. Save a separate semantic review with concrete resolutions and the exact batch fingerprint. Any copy, recipient, timezone, attachment, research or time change invalidates that review. Run lint again before approval and execution. Show only actual unresolved problems in the UI.

Changing a skill does not fix existing emails. If Andrew rejects current queued copy or asks for a batch rewrite, revoke those approvals immediately, cancel affected Gmail scheduled messages and verify cancellation, then rewrite the unsent records. Preserve sent history. Revised copy returns to review and requires new approval.

CLI (from the skill folder):

```
python3 scripts/campaign_lint.py check CAMPAIGN
python3 scripts/campaign_lint.py review CAMPAIGN REVIEW.json
```

Review JSON contains `fingerprint`, `reason`, `resolutions` mapping each warning code to a concrete explanation, and `semantic_checks` confirming thought continuity, distinct problem reasoning, grounded facts and appropriate subjects. This is the agent's critic record, not Andrew's approval to send.
