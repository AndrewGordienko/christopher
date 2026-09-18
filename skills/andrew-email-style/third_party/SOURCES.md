# Reused code and architecture sources

## Code included, pinned and licensed

- [Hiro-Inagawa/write-like-me](https://github.com/Hiro-Inagawa/write-like-me/tree/82797dd9239e5804654eaa26583aadd70f51221e), commit `82797dd9239e5804654eaa26583aadd70f51221e`: five unmodified Python modules under `write_like_me/` for stylometry, profiles, segmentation and deterministic checks. MIT license retained there. Andrew-specific configuration is separate in `references/voice-check.json`; generic upstream prose bans are disabled unless Andrew requested them. No model training or optional spaCy/textstat feature is required.
- [0xfe/ragmail](https://github.com/0xfe/ragmail/tree/210df4b5e5e94eac008d8899420f048336aedff9), commit `210df4b5e5e94eac008d8899420f048336aedff9`: unmodified `mbox_reader.py` and `email_parser.py` under `ragmail/`. MIT license copied from the pinned README. Local `scripts/ingest.py` subclasses parsing to preserve spacing and correctly parse quoted address names; it resolves threads from references/Gmail IDs instead of the upstream subject fallback. The upstream search/database environment is not installed.

## Workflow references, not installed integrations

- [Wingmate](https://github.com/KrishBakshi/wingmate): chat-driven local research and the distinction between a sourced signal and a value hypothesis. Our writer uses Sent examples rather than Wingmate's fixed templates.
- [OpenOutreach](https://github.com/eracle/OpenOutreach): a product/market request can drive discovery and qualification, with a JSON-lines boundary separate from sending. We use a local source/account contract; its paid provider, qualifier, sender and daemon are not installed.
- [Vercel email-agent](https://github.com/vercel-labs/email-agent): separate company/person research and persisted contact processing state. This implementation uses account JSON files, not its Neon/Outreach deployment.
- [GitHub email-drafter](https://github.com/github/awesome-copilot/blob/main/skills/email-drafter/SKILL.md): retrieve recent same/similar-recipient mail before drafting.
- [OpenKit skills](https://github.com/OpenKit-Ltd/skills): separate personal context from inbox voice.
- [Explorium GTM skills](https://github.com/explorium-ai/gtm-skills): structured research output separated from email composition. No Explorium connector is configured here.

## Deferred

[PanzaMail](https://github.com/IST-DASLab/PanzaMail/tree/cca13ad6ad04e3dbf4baeed91e3cc167d6d27319) supplies the instruction-playback/RAG/fine-tuning reference architecture; no training code or private-mail upload runs here. Its [original paper](https://arxiv.org/abs/2407.10994) is from 2024, so the pasted descriptions of it as a new 2026 system are not used as implementation evidence.

[ReCAP](https://github.com/holi-lab/ReCAP) is a future utility-retrieval research reference, not a trained email response model in this project. Contextual bandits and numerical reply predictions are deferred until suitable data and evaluation exist. Generic vendor reply percentages are not priors in the code.

No unverified research claims, vendor success percentages, or unidentified `sales-research-agent` repository have been copied into operational policy. The implemented provenance gate checks captured source IDs and quotes; semantic entailment/freshness remains a required model critic check.
