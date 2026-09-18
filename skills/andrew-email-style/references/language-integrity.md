# Final language-integrity gate

Run this after research, personalization, voice editing, external criticism and
user edits, immediately before approval or scheduling. It is a language check,
not permission to rewrite the email.

Read every sentence for grammar, punctuation, coordination, modifiers,
prepositions, relative clauses and idiomatic English. Ask whether a native
speaker would naturally produce this exact construction in an ordinary email.
Being technically parseable is insufficient.

Make the smallest correction to the failing construction. Preserve cadence,
informal vocabulary, sentence length, technical meaning and enthusiasm. Do not
regenerate the paragraph or polish already good sentences.

Inspect especially: “use X on Y”, “apply X somewhere”, “interested me as/in”,
“somewhere” followed by a clause, “which is what”, “a part of X is”,
“alongside X and” and “if there's something you need more”. These are inspection
prompts, not universal bans on grammatical phrases.

Examples:

- “Enthought interested me as somewhere…” → “Enthought seemed like somewhere…”
- “somewhere catching a problem earlier matters” → “somewhere where catching a problem earlier matters”
- “I'd be doing this alongside my current work and attached my resume.” →
  “I'd be doing this alongside my current work. I attached my resume for context.”
- “in London, UK working…” → “in London, UK, working…”. Keep UK because Andrew
  explicitly requested it; do not drop it to avoid the punctuation decision.

Record each changed sentence with BEFORE, AFTER and REASON. Read the full final
email again for both voice and language integrity. Review facts against the
current source packet. A deterministic pattern check catches known regressions;
it does not replace the sentence-by-sentence language review.

Save the final checks against the exact subject/body fingerprint. Every later
edit makes those checks stale. A stale external critique is not a current pass;
when external review was enabled, refresh it before scheduling. The external
critic remains advisory about wording and cannot override Andrew's instructions.

Approval and scheduling require current facts, grammar/idiom and voice checks,
verified recipient, matching attachments and a valid recipient-local send time.
Revalidate the timezone, source, local weekday/window and future time at execution.
Any stale or failed required check revokes eligibility. An already scheduled
message becomes cancellation-required, never silently repaired in place.
