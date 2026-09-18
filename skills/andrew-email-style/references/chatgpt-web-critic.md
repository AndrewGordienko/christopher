# Optional ChatGPT-web editorial review

Run only when enabled for the task or campaign. Andrew has enabled it for the September 2026 contract Wave 1 and the current Wapahki batch. His preferred voice-review context is his existing **Morrow** project in ChatGPT web, which contains his tuned writing context. Verify that the new chat is inside that project; a standalone ChatGPT chat is not equivalent. It is an advisory critic, not the writer, a source of facts, an approval, or a sending agent.

1. Finish recipient research, retrieve Sent/recipient history and select the candidate first.
2. In Andrew's existing signed-in Chrome session, start a fresh chat inside Morrow (unless he selects another context). Supply only the recipient's public role/company, objective, final subject/body and minimal context. Do not include mailbox exports, credentials, private third-party correspondence or email attachments. Prefer pasting the minimal draft text directly. A batch may contain separately identified drafts if each gets a specific review. Review eligible primary sends first, then held backups when the whole batch is requested; preserve individual coverage and exact text.
3. Ask for critique, not a rewrite, using the prompt below.
4. Save the actual comments, chat URL and observation time beside the draft. Preserve the exact before subject/body and hash.
5. Accept only narrow fixes compatible with Andrew's current instructions, task draft, Sent cadence and verified facts. Record accepted and rejected advice with reasons. Do not invent a change to satisfy the critic.
6. Run the normal Andrew voice and factual critic on the resulting draft. Store the after subject/body and hash. Later edits make this review stale; never display an old pass as a review of new wording.
7. Show a small status: not run, pending, reviewed/retained, number of issues fixed, or stale after edit. Keep full comments in the local record. No external veto or generic outreach rubric outranks Andrew.

Prompt:

> Review this email as a skeptical editor.
> Evaluate whether it sounds naturally written by a real person; whether anything is obviously AI-written, polished, corporate or salesy; whether the first paragraph is unnecessarily complicated; whether the sender's relevance is clear quickly; whether technical detail is at the right human abstraction level; whether recipient reasoning is genuine; whether the ask is natural; whether the subject is something a person would open; and which exact sentence is weakest.
> Do not make the email more formal. Do not optimize toward generic cold-email conventions. Give only specific problems and minimal suggested fixes.

`external-critic.json` records `status`, `chat_url`, `observed_at`, `before`, `before_hash`, `feedback`, `accepted_fixes`, `rejected_advice`, `after`, `after_hash`, and `outcome` (initially null). Store subject-only follow-up critique separately when subjects change during review. Match eventual outcomes through the draft/contact ID without claiming that critique caused a reply.

Unavailable Chrome/ChatGPT is recorded as unavailable. Do not claim the pass ran. The pass remains optional; the ordinary voice/fact gates still apply.

## Current project preference

Andrew explicitly selected his **Morrow** ChatGPT project for final verification because it contains his established voice context. Use that project when requested, with the current exact localhost drafts and latest user instructions. This overrides the generic fresh-chat preference. Ask for specific defects and minimal fixes; save the actual project chat URL and feedback. Older project examples must not override current instructions or exact user corrections.
