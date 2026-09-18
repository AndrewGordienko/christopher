# Passive history workflow

Preserve a supplied or existing task-specific draft before searching history. A draft excluded from the historical corpus may still be the primary writing seed for this task. Do not infer that it was sent or produced an outcome.

Use Codex's current model to interpret messages; these Python helpers do not call a separate LLM service. No manual labels or preference feedback loop is needed.

Verified Gmail accounts in Chrome are `gordienko.adg@gmail.com`, `andrew@gnk.software`, `andrew.g@outagehub.ca`, and `andrew@wapahki.com`. Each Chrome profile may use `/u/0/`; verify the account header before reading. Earlier user spellings were approximate.

Search current-recipient correspondence first, then comparable Sent Mail. Read original expanded messages, not Gmail summaries. A practical starting filter is `in:sent -label:"Apollo Mailwarming" -subject:"Blocklist Check Test" -subject:wbx` plus recipient or relevant task words. Read the received messages too. Exclude warmup, automated responses, self-account exchanges and copied quoted history. Do not discard an email because it seems AI-assisted; Andrew chose Sent Mail as the behavioral voice source. Current explicit bans still prevail.

Save a thread capture through `scripts/outbound.py thread thread.json`. JSON fields:

```json
{
  "id": "observed-gmail-thread-id",
  "account": "gordienko.adg@gmail.com",
  "source": "https://mail.google.com/mail/u/0/#sent/observed-thread-id",
  "observed_at": "2026-09-14",
  "complete": false,
  "subject": "Actual subject",
  "messages": [
    {"id": "actual-message-id", "kind": "sent", "sender": "gordienko.adg@gmail.com", "recipients": ["actual address or observed name"], "sent_at": "2026-09-01T10:00", "body": "Exact original text", "context": {"relationship": "warm", "objective": "research_visit"}}
  ]
}
```

Use actual data, not the illustrative values. Messages must be ordered; retain account/timezone ambiguity and clipping notes. The recipient list can include verified name and email aliases. Incoming kinds are `human`, `automatic`, `bounce`, `out_of_office`, `self` or `unknown`; do not treat a scheduling bot as human.

Infer relationship at the moment the email was sent; a later reply does not make earlier cold contact warm. Infer objective, department, seniority, industry and company size only as far as evidence permits. Missing history does not establish cold contact. A follow-up to unanswered cold mail is still cold. A human title such as HR assistant does not become automation manager because the message discusses robotics.

For semantic inference beyond the conservative baseline, Codex adds `annotations.context` or `annotations.outcome` to the sent message:

```json
{
  "value": {"type": "routing", "replied": true},
  "confidence": "high",
  "evidence": [{"message_id": "actual-downstream-human-id", "quote": "Exact supporting text"}]
}
```

A context annotation has `value` containing the inferred fields instead. Classification is done by the agent, not Andrew. Preserve ambiguous cases as unknown. Evidence quotes must exist; a human outcome must cite a downstream human message. Distinguish polite decline, routing, technical answer, positive interest, meeting proposed/confirmed and next step. A meeting proposal is not a completed visit, contract or investment. Attribute a reply conservatively when multiple sends precede it, including subject changes or parallel threads. Historical associations do not prove the wording worked.

Commands, relative to the skill directory:

```sh
python3 scripts/outbound.py thread /path/to/captured-thread.json
python3 scripts/outbound.py retrieve /path/to/current-context.json
python3 scripts/outbound.py index
python3 scripts/outbound.py status
python3 scripts/outbound.py outcomes --useful --after 2026-09-07
```

Current context is a flat JSON object with `recipient`, `relationship`, `objective`, `type`, `department`, `seniority`, `industry`, `company_size`, `organization`, `thought`, and optionally `current_facts`/`current_thread`. Unknowns may be omitted. Use `research_visit`, `schedule`, `acquisition`, etc. consistently; the agent resolves synonyms.

Context may also contain `supplied_draft` and/or `existing_task_draft`, each an object with original `body`, `source` (conversation, local file or observed Gmail draft reference), and optional `subject`. The supplied draft takes precedence. Keep exact text, not a summary. Do not put it in the sent corpus.

Resolve sender context before retrieval with `project` (Andrew's company/project), optional `sender_mode`, and `sender_fact_indices` selecting up to three `current_facts`. See [sender-context.md](sender-context.md). Retrieval returns `sender_context` alongside the seed and historical examples; `prepare` passes it to the writer. An unknown role stays unknown rather than loading a default biography.

Retrieval returns the selected `task_draft` and `drafting_priority` separately from `voice_examples`, `response_examples` and recent `recipient_history`. `prepare` carries the seed into the writer packet. The model checks matches for semantic fit and uses history to calibrate the seed, not overwrite it. The local implementation is metadata/lexical retrieval, not learned utility retrieval or embeddings. It builds a SQLite FTS index for local inspection, and does not train a response model. Select useful outcomes only among comparable relationships/objectives; count a thread once. Similar sent wording is deduplicated without discarding every repeated short acknowledgment.

Optional existing MBOX archives can be ingested with `python3 scripts/outbound.py mbox archive.mbox --account <verified-account>`. RAGmail's pinned parser reads encodings and MIME; the adapter preserves paragraphs and short replies, handles quoted display names, strips clear quote boundaries and links threads by message references/Gmail IDs rather than subject alone. The v1 importer holds the archive's parsed messages in memory. A Sent-only export cannot establish response absence. Do not require an export when live Gmail is available.

Private captures/indexes stay in `data/`, excluded from version control and never served by the localhost draft page. Current coverage and limitations are in [mailbox-coverage.md](mailbox-coverage.md). The nightly Codex preparation job refreshes Gmail when the local browser is accessible; it is not a Gmail push subscription. Fine-tuning is not installed.
