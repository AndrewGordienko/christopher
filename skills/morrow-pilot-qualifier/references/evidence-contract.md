# Cell evidence contract

Store under `campaigns/<campaign>/accounts/<facility>/research.json` as `cell_qualification`; mirror it to `cell-qualification.json` for inspection.

Required fields: `schema_version:1`, `status:QUALIFIED|POSSIBLE|HOLD`, `qualification_score:0..7`, `facility_id`, `cell:{id,name,equipment,task}`, `criteria`, `reason`, `reviewer`, `reviewed_at`, `physical_only`, `requires_safety_bypass`, `next_action`.

The seven criteria are `cell_identity`, `operating`, `recurring_human_recovery`, `software_recovery`, `observable_state`, `technical_owner`, `operational_benefit`. Each has `status:CONFIRMED|LIKELY|UNKNOWN`, `statement`, and `basis:[fact_ids]`. A LIKELY judgment needs `inference`. UNKNOWN may have an empty basis. Use null for unresolved cell fields. Supported criteria must cite facility/cell-specific facts, including a person's relationship to that cell; a person's general title alone is not enough. The technical-owner criterion additionally names `person_id` matching a researched stakeholder.

`qualification_score` equals the count of criteria with supported statuses. QUALIFIED requires all seven, complete cell identity, an evidenced owner, `physical_only:false` and `requires_safety_bypass:false`. These are research judgments with evidence, not authorizations to observe or control equipment. Physical-only or safety-bypass-dependent candidates must be HOLD.

Preserve observation date versus publication/event date. An old installation report proves historical installation; it may support LIKELY operation only with additional current evidence and an explicit rationale. It does not establish repeated faults, telemetry retention or controller access.

The writer receives a qualification fingerprint. Save separate `outbound-reviews.json` with `draft_hash`, `qualification_hash`, and `thought_continuity`/`cold_email_skeptic` objects. Each review requires `passed:true`, `reviewer`, `reviewed_at` and `reason`; the skeptic also records all six answers (`specific_reason`, `problem`, `technical_plausibility`, `small_ask`, `founder_voice`, `routing_reply`) as nonempty explanations. A text or qualification change invalidates these passes. Existing language, factual and enabled external-critic checks remain necessary.
