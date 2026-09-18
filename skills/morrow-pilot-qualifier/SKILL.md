---
name: morrow-pilot-qualifier
description: Qualify specific deployed robotic or automated cells for Morrow/Wapahki recovery pilots before any outreach is drafted. Use for pilot prospect selection and requalification; not paid technical-contract targeting.
---

# Morrow Pilot Qualifier

Never compensate for weak account research with stronger prose. If we cannot explain why a particular machine at this facility could have a Morrow-recoverable failure, do not write the email.

Run this gate first, using available evidence. Missing evidence routes to [morrow-account-research](../morrow-account-research/SKILL.md), then back here. `QUALIFIED` alone permits the strategy/writer stages. `POSSIBLE` means research more. `HOLD` means no outreach. Preserve older drafts as held history, not sendable copy.

Look for one deployed discrete cell, a known task, recurring human intervention, and a plausible repeatable controller/PLC/robot/vision/sequence recovery. Establish observable state, a relevant local technical owner, and a concrete operational benefit. Equipment may be likely operating when supported by specific evidence and a reasoned assessment; label that uncertainty. A generic vendor capability or executive title is insufficient.

Useful candidate mechanisms include pick/vision failures, part-not-found, gripper-state faults, PLC/robot mismatch, sequence timeouts, missing downstream acknowledgments and repeatable resets/restarts. A missed pick does not itself establish a stopped robot or a human recovery. Downstream manual sorting is not evidence of robot fault recovery. Safety resets are not permission to bypass interlocks or automate a safety function.

Do not qualify automation, optical sorting, downtime, maintenance staff, expansion, or machinery alone. Physical clearing, cleaning, blade replacement and broken components may cause substantial loss without establishing a software recovery case. A mixed intervention can qualify only when its software-addressable portion is separately evidenced.

Persist `cell_qualification` in the facility's `research.json`, with the [evidence contract](references/evidence-contract.md). The required `qualification_score` is the count of supported gates, 0–7, not a probability or a substitute for any missing gate. Evidence is CONFIRMED, LIKELY or UNKNOWN; LIKELY needs its supporting facts and inference. Only all seven supported gates plus a named cell/task/equipment/facility and a reasoned reviewer assessment can be QUALIFIED.

Report the exact cell, equipment, task, source evidence, likely human recovery, software mechanism, local owner, unknowns and next action. A shortlist is not qualification. Keep one active contact per company group; several GFL or Merlin facilities do not authorize simultaneous company touches.

The repository's `research.writer_packet` enforces the gate; readiness and queue checks enforce it again. Source quote validation precedes qualification. Semantic entailment remains the researcher's responsibility. Sending remains separately authorized under the [Andrew workflow](../andrew-email-style/SKILL.md).
