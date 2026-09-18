# Separate critic pass

For campaigns, finish with [the collection-level review](scheduling-and-batch-review.md#campaign-level-critic). Individual voice checks do not substitute for comparing company reasoning, project ideas, subjects, endings and timestamps across the batch.

After drafting, stop composing and read each candidate against Andrew's current thought, thread, selected research packet and the actual retrieved Sent examples. Do this internally; Andrew does not grade or label candidates.

Which exact sentence would he call AI? Check for professionalized plain language, unnecessary polish, artificial enthusiasm, forced research, mechanical short sentences, consultant scope and a generic closer. Preserve useful semicolons. Match the relationship's natural rhythm rather than a word count. Facts from historical mail are style context, not current factual permissions.

Before scoring, require:

- Every factual claim is supported by current context or source evidence. Check entailment/entity/freshness, not just source-ID existence.
- The thought and intended stage/ask are preserved. A research visit is not silently upgraded to a pilot.
- Apply [thought continuity](thought-continuity.md) at each paragraph boundary. Reject independently assembled biography/company/CTA paragraphs; add only the smallest true bridge needed for one thought to lead to the next. Contract first touches use the [current cadence and small-contract ask](contract-useful-work.md), not older company-hook examples. Other exploratory modes can use "a project I could take ownership of" where appropriate.
- Research remains mostly invisible and uncertainties remain hypotheses.
- Plain wording and appropriate sentence movement are preserved.
- Apply [impact-first motivation](impact-first-motivation.md): reject invented sector passions, generic moral claims, or a societal-outcome claim that the source does not support. The concrete outcome should connect to the company's technical work and Andrew's current skills without requiring a separate social-good preface. For this Contract Work batch, use Andrew's current short, concrete technical-topic subjects instead of self-focused student/skills pitches.
- When sender context is present, `sender_context_fit` must be true: the right role for the objective, relevant current facts, no unrelated company, stale biography or unsupported fundraising status. Context does not require inserting a biography into an otherwise complete draft.
- For exploratory contract outreach, check individual-first framing: Andrew's work, interest and ownership, without an unnecessary team-capacity pitch. Ownership must not become a false promise of sole execution. Answer team questions honestly and disclose actual collaborators when the scope calls for them; do not add them speculatively or ban legitimate "we" phrasing in other modes.
- Apply the [compression check](human-compression.md#final-compression-check) to explanations of Andrew's work and company research. Reject component inventories when a simpler true phrase preserves the relevant mechanism; also reject compression into generic skills, broader claims or lost uncertainty.
- When a task draft exists, its strongest task-specific substance and useful technical detail survive at the right abstraction. `technical_detail_preserved` means the relevant idea survives, not that implementation nouns remain verbatim. Andrew's current request to compress outranks an older longer gold example. Record the specific reasons for edits; historical-average cadence or arbitrary shortness is not a reason.

Save candidates as a JSON list of `{id, subject, body}`. Critic JSON is keyed by candidate ID:

```json
{
  "candidate-a": {
    "facts_supported": true,
    "thought_preserved": true,
    "plain_language_preserved": true,
    "research_quiet": true,
    "stage_correct": true,
    "sender_context_fit": true,
    "task_draft_preserved": true,
    "technical_detail_preserved": true,
    "draft_change_reasons": [],
    "voice_fit": 4.5,
    "recipient_fit": 4,
    "ai_sentence": null,
    "reject": false,
    "phrase_flags_reviewed": true,
    "research_fact_ids": [],
    "response_evidence_ids": [],
    "response_reason": null
  }
}
```

Use `voice_fit`/`recipient_fit` on 0–5, comparative judgments rather than learned probabilities. Cite only retrieved response-example IDs if comparable patterns inform a near-tie; explain the connection without attributing causality. Missing relevant outcome evidence contributes nothing. Do not lower voice quality to chase replies.

`python3 scripts/outbound.py rank candidates.json retrieval.json critic.json --packet writer-packet.json --save drafts.md`

Omit `--packet` for a simple reply with no account research. When a `task_draft` exists in either the packet or retrieval result, `task_draft_preserved` and `technical_detail_preserved` are required critic gates before ranking. These are semantic judgments from the critic, not automatic textual-similarity measures. `draft_change_reasons` records why any edits were needed; do not reward arbitrary verbatim copying over factual corrections or current instructions.

The command runs pinned write-like-me measurements and Andrew's configured deterministic check; no universal prose baseline, ideal word count or semicolon quota applies. It rejects missing critic gates and hard bans, then ranks voice/context. Response associations only break close ties. Metrics are diagnostics, not a clone-confidence score.

If no candidate passes, repair and repeat; never return a failed draft just because it scored highest. Return one finished email. No thumbs, gold promotion, manual labels, external training call or send operation is part of this loop.
