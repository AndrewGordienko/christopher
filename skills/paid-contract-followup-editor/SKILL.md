---
name: paid-contract-followup-editor
description: Edit Andrew's unanswered paid technical-contract follow-ups using his current supplied voice and work-to-motivation reasoning. Select one primary contact per company. Not first touches, second-person introductions, or replies to an active conversation.
---

# Paid Technical Contract Follow-Up Editor

Use Andrew's finished, selected messages before generic follow-up heuristics. The current evidence is [29 Gmail-scheduled follow-ups reviewed on September 17, 2026, with four exact examples](references/chosen-scheduled-examples.json). Read Nathan for the overall voice and Jeaffrey or Sajjad for the company-specific bridge. The [current Nathan reference](references/current-example.json) supplies the shared factual language and lint settings. These are user-selected scheduled messages, not evidence of successful replies. Later explicit user edits take precedence.

This supersedes the earlier short-only rules. The chosen batch is 289–314 words; aim around 300 when recreating this developed follow-up, with a 320-word editing guard. Do not pad to a word count or compress the causal argument into a bump. Short bumps remain a separate mode when requested or when the motivation has already been explained in the thread. Do not put this entire follow-up into first touches, active replies or unrelated job applications.

Use the [Andrew workflow](../andrew-email-style/SKILL.md) for original Sent/thread retrieval, current response state, factual context and local persistence. These are same-thread follow-ups; keep the original subject. A draft or editorial SEND status never authorizes mail delivery.

## Current reasoning and voice

Keep four connected beats, with ordinary paragraph transitions:

1. **Relevant work:** Andrew's general planning/search algorithms execute biological workflows on robotic labs, handling deadlocks, resource conflicts and failure cases; digital twins test plans before hardware. The latest supplied paragraph says this co-op work with the named teams has been happening since May. The user supplies the direct work with Anthropic and NVIDIA teams as factual context.
2. **Why that changes how he spends his time:** one paragraph moves from proximity to the work, to concern about unequal benefit, to the Sierra Leone/TB contrast, to his personal decision about his time. Preserve the plain admission “Partly for my own morality” when reproducing this mode. Do not restore the one-introduction-away-from-Anthropic's-CEO sentence: Andrew omitted it from every chosen message.
3. **Why this company and this contract:** write a specific continuation about air quality, water loss, wildfire detection, energy reliability, medical access or the actual work in the original thread. Offer a **4–6 week paid contract**, refer to the original idea as one possibility, and prefer a problem the team already wants solved.
4. **Execution and a natural close:** he works intensely, takes ownership and gets unfamiliar problems to something concrete quickly. Never guarantee a positive result. Preserve the simple call invitation without adding a resume/referral/timing checklist.

The shared factual and moral passages may stay stable when asked to recreate this style. Customize the company connection and original technical thought. Do not paraphrase settled language merely to make every email different. The company paragraph must connect a mechanism to an understandable consequence: better signal plans can save commute time and fuel; stronger vessel detection can help protect fisheries. Then connect one relevant skill to that mechanism. Keep outcomes conditional where unproven. “Real-world impact” alone is not enough.

Use five prose paragraphs: work, motivation, company connection, conditional contract plus execution, natural close. Describe the work in execution order: new workflow → planning/search → deadlocks/resource conflicts → digital-twin check before hardware. One earlier technical idea is enough. The company paragraph and the short idea/team phrase in the ask carry most of the customization. The selected close has no question mark; do not force a backlog question, call duration or stacked resume/referral request.

Sound personal, technically fluent, reflective and conversational. Do not turn the concern into a criticism of the recipient or claim their work is morally superior. Do not call NVIDIA a frontier AI lab. No em dashes, exaggerated performance promises, invented projects or guaranteed delivery outcomes.

## Facts and hypotheses

- Preserve user-supplied work facts; do not promote them into independent verification, endorsements, customer status or access to proprietary data. The named-team paragraph is part of Andrew's selected voice, not permission to add other prestigious names. Check time-sensitive wording such as “Since May” and “co-op” against current sender context before reusing it in a later season.
- Longevity/access concerns are Andrew's viewpoint. Do not state that AI has cured aging or that the recipient's work has proven public benefit.
- Sierra Leone remains a WHO high-TB-burden example; use unequal access to existing prevention/diagnosis/treatment, not an unsupported claim that TB vaccines were priced out. Sources are recorded with the current reference.
- A 4–6 week contract is Andrew's proposed engagement window. It does not require evidence that the company already scoped or budgeted one. Keep “if there is” and scope the actual work after a response.
- Read the original thread. Avoid restating the student introduction, claiming new research you did not do, or inventing a live backlog. Mention one original technical idea conditionally.

## Company-level routing

For newly prepared outreach, default to **one PRIMARY FOLLOW-UP per company** and hold coworkers. The observed batch includes multiple coworkers; that is Andrew's existing selection, not an inferred instruction to repeat that routing in every future campaign. Preserve user-authored schedules. Learning the writing style does not authorize cancelling, rescheduling, rewriting or sending any email. Apply explicit current routing instructions over the default.

Explicit declines are **SKIP**. Close the contact without another pitch. Handle a genuine opening, referral or active reply as a conversational response, not an unanswered follow-up.

## Review and persistence

1. Preserve the supplied writing seed separately from sent history. Read original messages, roles and reply state before adapting it.
2. Save the company-specific reason and technical connection before the writer pass. Keep capability, personal concern, sourced public fact and buyer hypothesis distinct.
3. Read the complete final draft separately for continuity, then as a skeptical recipient. Check whether the concern follows from the work and the company choice follows from the concern; repair only actual defects.
4. Keep the proposed contract conditional and the reply simple. Check grammar, readability, unsupported claims and guarantees against exact final text.
5. Run [followup_lint.py](../andrew-email-style/scripts/followup_lint.py). It preserves original-thread/routing guards, rejects guaranteed results, repeated student introductions, multiple question marks and em dashes, and checks cross-company shared text outside the exact user-approved spans in the reference. The maximum length now follows the latest supplied reference, not the superseded 120-word ceiling. Stable approved context is allowed. Semantic review still checks company-specific relevance; lint alone is not approval.
6. Archive superseded drafts, replace the current campaign artifacts and CRM bodies, and bind new review records to the final text. Preserve sent messages, subject/thread IDs, primary/hold/skip decisions and Gmail state.

## Output

For each company/contact save:

```text
### Company — Contact
STATUS: SEND / REWRITE / HOLD / SKIP
WHY:
One sentence explaining the decision.
DRAFT:
The finished follow-up, or no draft for a closed contact.
```

Keep CRM labels explicit: PRIMARY FOLLOW-UP, HOLD, SKIP, or REWRITE when checks fail. Report the completed batch and links without a long explanation of the editing process.
