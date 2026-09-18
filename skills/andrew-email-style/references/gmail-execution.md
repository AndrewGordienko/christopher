# Gmail execution after individual approval

Andrew's current instruction is to prepare all messaging for review and send/schedule nothing until he approves each email individually in a.outbound. Research, a gold exemplar, a saved draft, a batch request or a previous draft's approval is not approval of a new email.

After individual approval, Codex may use the existing signed-in **Chrome** Gmail session to schedule that exact email. The localhost app stores approval and state; it does not control Chrome by itself. A batch command such as "Schedule all approved emails for tomorrow" executes only already individually approved records. Never bulk-approve or approve on Andrew's behalf.

## Sender, attachments and time

- Contract Work: `gordienko.adg@gmail.com`.
- Wapahki: `andrew@wapahki.com`. Andrew confirmed the spelling in Gmail's account list. Do not use `wahpaki.com` or substitute his personal account if sign-in is unavailable.
- Other workspaces require their own confirmed sender; do not infer authorization from a logged-in account.
- Reuse the verified resume manifest at `.runtime/attachments.json`. The selected file is `A. Gordienko F2026.pdf`, originally resolved by its exact name and Purple Finder tag. Recheck filename, file existence and SHA-256 before attachment. Do not choose a numbered duplicate, regenerated PDF or another resume silently.
- Initial Contract outreach does not attach that resume by default. Offer to send it over; the manifest is available for a later request or Andrew's explicit attachment instruction, not an automatic upload.
- Link intended attachments to the current draft fingerprint before approval and display their filenames in review. A local file manifest does not mean Gmail has received the attachment. Verify upload completion and exact filename in Compose before scheduling.
- The approval binds recipient, From mailbox, subject, body, attachment paths/content hashes, thread, labels, recipient IANA timezone and UTC send instant. Any change requires individual reapproval.
- Follow [scheduling and batch review](scheduling-and-batch-review.md). Prefer weekday 08:30–11:30 recipient-local windows, with afternoon slots only when context permits. Use DST-aware conversion, never a fixed EST/PST offset. Respect mailbox capacity and variable spacing, at least ten minutes apart by default; do not create an exact ten-minute sequence or compress an approved spread into a burst.
- The Gmail picker may show the sender/browser timezone. Establish its actual timezone and convert the approved UTC instant into that zone. Verify the resulting instant matches recipient-local approval. If unclear, stop that action.
- Never click ordinary **Send**. Open **Schedule send**, choose the approved date/time and verify it. A passed or imminent slot requires a new proposal and approval; do not send immediately or silently move it to tomorrow.

## Execution procedure

1. Run `python3 scripts/execution.py approved --date YYYY-MM-DD` (paths relative to the skill). This date means the app's Europe/London queue day; each record retains recipient-local date/time. Skip everything held, unapproved or already attempted.
   The campaign lint and its semantic review must match the current batch. A prior pass does not cover changed copy or timestamps. A request to redo the emails revokes their previous approvals.
2. Refresh the actual account/thread in Gmail, checking for replies, sent messages and existing scheduled copies. Sync genuine observations to the database. A human reply pauses the company. Never infer an empty thread from a stale search or another mailbox.
3. Claim exactly one record with `execution.py claim ACTION_ID --approval-hash HASH`. Claims persist across crashes. An existing attempt requires reconciliation, not a second compose.
4. Verify the visible Google Account identity and actual Compose From address. Create the approved first touch, or use the original thread for a follow-up. Fill exact recipient, subject and body; remove automatic signature text if it would alter the approved body. Check CC/BCC are exactly as approved (normally empty).
5. Attach only the approved file(s), using the supported Computer Use file chooser. Read its upload documentation first. Verify filename and upload completion. Do not rewrite an attachment sentence instead of attaching.
6. Apply the managed workspace/status labels under [gmail-labels.md](gmail-labels.md), preserving all unrelated labels. A scheduled email gets Scheduled; no stale Follow-up Due or Needs Review.
7. Open Schedule send and enter the correctly converted approved time. Capture exact visible fields in a private observation JSON: `sender_mailbox`, `recipient`, `cc`, `bcc`, `subject`, `body`, `attachment_filenames`, `labels`, `scheduled_at` (timezone-aware instant), `observed_at`, `source` (actual Gmail URL), `tool_ref`, and existing `thread_id` if replying. Run `execution.py preflight ACTION_ID OBSERVATION.json` immediately before the final scheduling click. A mismatch stops the action.
8. Click **Schedule send**, then open the message under **Scheduled**. Verify actual recipient, sender, full subject/body, attachment filenames and displayed schedule again. Capture `folder:"Scheduled"`, the observed thread ID/URL and message ID only if actually available. Do not invent opaque Gmail IDs or treat a toast alone as proof of all fields.
9. Run `execution.py confirm ACTION_ID VERIFIED.json`. This records `gmail_scheduled`, not Sent. Actual sending is recorded only after a later Gmail observation confirms it happened.
10. If interrupted or uncertain after a click, run `execution.py reconcile ACTION_ID --reason "..."`. Inspect Gmail before any retry; never create duplicates to recover from uncertainty. Continue independent approved records only when doing so cannot contact the same company or violate spacing.

The final report distinguishes scheduled, still awaiting approval, blocked and needing reconciliation. Include the actual scheduled time and Gmail link for successes. Do not claim that adding this workflow proves a live send has been tested.

## Replies and cancellation

Sync mail before execution and during nightly preparation. If an account replies, cancel remaining local no-response actions. If a message is already in Gmail Scheduled, mark it cancellation-required, cancel it through Gmail's UI and verify it left Scheduled before recording completion. Local state alone cannot cancel a Gmail delivery. Preserve its draft when cancellation returns it to Drafts. An uncertain cancellation needs attention immediately.
