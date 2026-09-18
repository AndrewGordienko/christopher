# Operational Gmail labels

This replaces the earlier company-label proposal. Never create company, person, campaign, wave or touch labels. Research stays in a.outbound until correspondence exists; no Researching label is needed.

Root: `a.outbound`.

Every managed outbound thread gets the root and exactly one workspace:

- `a.outbound/Contract`
- `a.outbound/Wapahki`
- `a.outbound/OutageHub`

Every active thread gets exactly one primary status:

- `a.outbound/status/Scheduled`
- `a.outbound/status/Awaiting Reply`
- `a.outbound/status/Reply Needed`
- `a.outbound/status/Meeting`
- `a.outbound/status/Opportunity`
- `a.outbound/status/Closed`
- `a.outbound/status/Do Not Contact`

Temporary actions can coexist with a status:

- `a.outbound/action/Follow-up Due`
- `a.outbound/action/Needs Review`

SQLite is the source of truth. `scripts/gmail_labels.py` derives expected labels from recorded thread/touch, scheduling and opportunity state. Codex applies the diff through Chrome, then verifies actual labels and records that observation. Never treat a planned diff as a completed Gmail mutation.

Scheduled means verified under Gmail Scheduled. Actual sent mail becomes Awaiting Reply. A human reply removes Awaiting Reply and Follow-up Due and becomes Reply Needed; a later actual Andrew reply can return it to Awaiting Reply. A confirmed meeting becomes Meeting; a proposal to meet is still Reply Needed. A real sourced project/pilot/API opportunity becomes Opportunity. Finished, declined or abandoned threads become Closed. Bounce, unsubscribe and explicit do-not-contact requests become Do Not Contact and permanently suppress future outreach to the address.

A due no-response follow-up can have Follow-up Due. Remove it as soon as the follow-up is scheduled/sent or a reply arrives. Needs Review is removed on approval/scheduling. Do not leave multiple primary statuses from earlier lifecycle stages.

Reconcile after syncing messages, changing an opportunity or executing/canceling a schedule. Preserve existing unrelated labels, including `contracts`. Remove only obsolete labels in this managed taxonomy. A user-edited Gmail label is a discrepancy to inspect against the actual thread and database, not permission to erase business history or revoke suppression.

For an uncertain DB/Gmail mismatch, first inspect the complete thread, update sourced state if new mail explains it, then repair labels. Never infer that mail was sent from a label alone. Persist observed labels, expected labels, additions/removals, Gmail URL and observation timestamp; an inaccessible mailbox remains pending.

The UI exposes Reply Needed, Follow-up Due, Scheduled Tomorrow, Active Opportunities and Do Not Contact shortcuts. Gmail date search is not assumed to filter scheduled delivery timestamps: the app filters tomorrow's exact queue instants and provides Gmail links for those records, plus a general Scheduled outreach search.

## Reconciliation commands

- `python3 scripts/gmail_labels.py pending` derives missing/stale reconciliation work for existing observed threads.
- Capture `mailbox`, `thread_id`, `labels`, `source`, `tool_ref` and `observed_at` from Chrome. Run `python3 scripts/gmail_labels.py plan CONTACT before.json` after the thread sync. Do not apply a plan with `requires_thread_refresh` or a workspace conflict.
- Apply only the plan's managed additions/removals, then capture the resulting labels. Include `previous_labels` and the plan's `expected_hash` in the after-observation.
- `python3 scripts/gmail_labels.py confirm CONTACT after.json` verifies the mailbox, thread, current database state, recent observation, exact managed-label set and preservation of unrelated labels before recording a receipt.

No receipt means pending, not synchronized. Changed database state invalidates the old expected hash; reconciliation checks return every 24 hours even without a local state change. The nightly Codex task executes these browser steps when its mailbox connection is available. The Python module itself does not access Gmail.
