---
name: email-thought-continuity-editor
description: Critique Andrew's outbound email as a chain of spoken reasoning after drafting. Use to detect disconnected facts, motivation, pilot scope and CTAs; not stylistic polishing.
---

# Email Thought Continuity Editor

Read the complete selected draft separately from composition. For every sentence ask why Andrew says it immediately after the preceding sentence. It should explain, narrow, substantiate, show a consequence, or lead naturally to the ask.

For an unanswered paid-contract follow-up, first read the [selected scheduled examples](../paid-contract-followup-editor/references/chosen-scheduled-examples.json). Review their intended chain: the work he sees → his personal concern → a concrete reason this company's work matters and fits his skills → a conditional 4–6 week paid contract → execution and a natural call. The stable work and moral paragraphs are intentional. Judge whether the company-specific bridge follows; do not delete the motivation merely to make a shorter technical pitch. These messages omit the older CEO-proximity sentence.

Flag topic jumps, facts inserted only to prove research, unsupported motivation, a pilot unrelated to the observed mechanism, an abrupt CTA, independently written paragraphs, or paragraphs that can be shuffled without affecting meaning. Individually grammatical sentences do not establish a coherent email.

For a pilot, the reasoning should connect the specific cell to conditional human recovery, explain why that matches the work, and lead to one small observation/test and a conversation. Never repair an absent cell/recovery fact with a better transition: return RESEARCH MORE.

Return PASS or EDIT with the exact broken connection and the minimum repair. Do not rewrite for elegance or arbitrary brevity. Re-read the whole draft after a change. Record the final draft hash, qualification hash where applicable, reviewer, time and reason in `outbound-reviews.json` under `thought_continuity`. Then run [cold-email-skeptic](../cold-email-skeptic/SKILL.md).
