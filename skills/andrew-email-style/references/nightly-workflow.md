# Nightly preparation and thread state

## Current cell gate (September 2026)

For new Morrow/Wapahki pilot outreach, [morrow-pilot-qualifier](../../morrow-pilot-qualifier/SKILL.md) and the other five linked stages in the main skill supersede older automation-only selection, plant-wide baseline offers and volume targets below. A scored QUALIFIED cell is required before writing; POSSIBLE means more research, HOLD means no outreach. Historic examples remain history. First scope: one cell, passive faults/actions/restored-state observation, repeatable human intervention time, then one separately authorized suitable recovery. Neither a robot installation nor downstream manual sorting proves recurring operator recovery. The UofT student identity is supported; a formal university research-project affiliation requires separate evidence.

Apply [the CRM operating contract](crm-and-sequencing.md) and [scheduling/batch review](scheduling-and-batch-review.md). Resolve orphaned active relationships, prioritize human replies and opportunities, and compare the selected campaign before approval. A request to rewrite current copy invalidates its approvals and requires actual cancellation of affected Gmail scheduled messages.

Use `scripts/operations.py` as the boundary to `.runtime/outbound.sqlite3`. The database is the source of truth for contact/thread state, touches, pending actions, events and outcomes. Markdown/JSON drafts and research are supporting artifacts, not evidence an email was sent.

The local launchd job runs once around 23:00 Europe/London, using `scripts/nightly.py --scheduled`. It needs the Mac awake, Codex authenticated and Chrome/Gmail accessible. It starts `codex exec` with the repository instructions, preserves logs privately, uses a lock to prevent overlap and records running/completed/failed/timed_out. A successful process exit is not proof every mailbox synced: inspect holds and limitations. Missing Gmail access must leave contacts held; never manufacture a sync. No sending endpoint exists.

Daily capacity defaults to 30 across all three workspaces, including follow-ups. Prepare fewer when fewer qualify. Prioritize sourced fit, recipient ownership, genuine pressure/recency and relationship value. These are ordinal judgments, not learned probabilities. Never manufacture scores for project probability. One account and one email address per queue day; alternate people and follow-ups must not collide.

Read the persisted Calendar relationship plan before each account decision. Its review date, target and technical brief survive refresh until new mailbox evidence changes the relationship. A review is not permission to send. The Calendar's shared date-specific target is read by `build_queue`; actual sends already recorded that day consume capacity alongside pending sends. Do not allocate 30 new slots after 30 have already gone out. Next-person choices preserve the previous sent thread as history and require a separately verified recipient and fresh account decision before drafting.

## During each run

For Wapahki opportunities, process the [LOI qualification and post-meeting next action](wapahki-loi.md) after each substantive positive conversation. Update the champion/authority path, produce the local brief, and recommend an LOI ask when qualified. Do not leave a qualified case at conversation without an owner and next action. Sending a brief/LOI is separate from preparing it.

1. `operations.py import` reconciles sourced campaign drafts into shared contacts. Select the actual sending mailbox in each person's context; do not choose Andrew's biography from that mailbox alone.
2. Read current Gmail threads and search initial contacts for existing history. Capture identity, message IDs, original subject, actual sender, recipient, timestamps, complete body and full-thread observation time. Immediately `operations.py sync CONTACT CAPTURE.json` for each. Imports must include complete current threads, not a clipped final message. Use timezone-aware dates; do not infer timestamps from ambiguous UI labels.
3. Run `signals.py poll`. Inspect new/changed job descriptions and pressure sources; perform sourced triage before updating account strategy. A failed/capped ATS feed does not prove roles closed. Refresh official company/recipient context before follow-up decisions.
4. For due people, retrieve same-person history and 3–5 comparable Andrew emails, plus comparable useful replies. Keep the same mailbox, thread and original subject. Do not regenerate future follow-up bodies on day zero.
5. Decide SEND / WAIT / COMPLETE, using `operations.py decide CONTACT DECISION.json`. SEND means **prepare for review**, never deliver. WAIT requires a future reconsideration date. COMPLETE stops this sequence. A user-requested restart needs a new explicit reason and current research, not silently resetting touches.
6. Draft the due body, separately critique it, then `operations.py queue --date YYYY-MM-DD --capacity 30`. Keep new actions in review. Preserve individually approved records only when recipient, sender, content, attachments and exact time are unchanged. Spread new recommendations at least ten minutes apart in recipient-local working hours, including sensible afternoon slots. Never silently move an approved time.
7. Reconcile the fixed `a.outbound/*` labels against sourced database state using [gmail-labels.md](gmail-labels.md). Preserve unrelated labels. Nightly preparation does not approve or schedule emails. Individually approved execution is a separate Chrome step under [gmail-execution.md](gmail-execution.md).

## Capture example (shape only)

```json
{
  "account": "selected-sending-mailbox",
  "id": "actual-gmail-thread-id",
  "source": "https://mail.google.com/mail/u/0/#all/actual-id",
  "tool_ref": "actual-browser-capture-reference",
  "observed_at": "2026-09-14T22:00:00+00:00",
  "complete": true,
  "subject": "Actual original subject",
  "messages": [
    {"id":"actual-id","kind":"sent","sender":"actual-sender","recipients":["actual-recipient"],"sent_at":"2026-09-10T09:00:00+00:00","body":"Exact original text"}
  ]
}
```

Before a first touch only, a complete observed recipient search may have `id:null`, `messages:[]`. Record the exact query and observation; don't count unsent drafts as messages. A search miss cannot erase a known sent thread. Actual replies must match the person, and bounces must be linked to the original thread. Multi-person threads require explicit routing instead of attributing everyone’s response to one lead.

Incoming kinds: human, out_of_office, bounce, unsubscribe, automatic, unknown. Human outcome values: positive, routing, technical_answer, meeting_proposed, meeting_confirmed, next_step, declined, human. Unknown incoming mail pauses the sequence for inspection. Any human reply cancels remaining no-response actions. Bounce/opt-out/explicit decline suppress the same address across workspaces. An OOO with `return_at` defers until after return; without a return date, defer seven days and re-check. Do not count an OOO as a useful human response.

Cadence eligibility opens on local D3, D8 and optional D15 after the actual initial send, targeting D3–4, D8–10 and D15–18. Use weekday recipient-local windows, with the current 08:30–11:30 morning prior unless Andrew authorizes another window. Weekends or missed preparation can defer beyond a target range. Last touch requires explicit `still_worth_pursuing:true`. Touch2 clarifies/resurfaces the real question; touch3 adds a real new technical thought/result/event/narrower ask; touch4 lowers friction only if still warranted. No generic bump, fake urgency, recycled biography or prewritten sequence.

A follow-up decision contains `action`, `reason`, exact `snapshot_at`, `research_version`, `research_checked_at`, `new_reason`, `body`, `critic_passed:true`, optionally `followup_value` (0–1 judgment) and final-touch `still_worth_pursuing`. Ground external factual additions in current research sources. A new technical hypothesis may be a thought, clearly expressed as one. The caller resolves the semantic choice; the deterministic state layer validates freshness, continuity, stop conditions and capacity.

Analytics attribute an incoming reply to the nearest preceding observed touch in that thread, count each contact once per outcome/touch and distinguish proposed/confirmed meetings from completed meetings. This is descriptive attribution, not proof the wording caused a reply.
