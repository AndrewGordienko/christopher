# Human abstraction and compression

Use this to diagnose explanations whose scaffolding obscures the idea, including sender context and company research. It is not an instruction to compress every sentence. For Contract Work, [preserve the original thought](contract-preserve-thought.md) governs: developed mechanisms and natural continuity outrank brevity.

Ask: What is the simplest true description that lets this recipient understand why this matters?

Use the highest abstraction that preserves the relevant idea. Do not reproduce an internal technical description just because it is accurate or sounds impressive. Do not compress so far that the result could describe anyone.

## Abstraction ladder

| Level | Example |
| --- | --- |
| Implementation | Building CP-SAT scheduling systems, Tarjan-based deadlock detection, deterministic recovery search and simulation tooling. |
| System | Building search and planning systems that find failures and recovery paths in large automated systems. |
| Domain | Working on search, planning and simulation for biotech automation. |
| Generic | Working on AI and robotics. |

Choose the highest useful level, not the highest level available. "AI and robotics" usually loses the reason Andrew is relevant. A domain description plus one system-level phrase often gives the clearest picture:

> I work on search, planning and simulation for biotech automation, mostly around finding failures and recovery paths in large systems.

These examples illustrate phrasing, not reusable facts about Andrew. Current context must support the work, location, employer and status.

Descend into implementation detail only when the recipient can use it and the mechanism establishes credibility or directly connects to the problem. Being technical is not by itself a reason to list every method.

## Compress before adding

Try to express each relevant idea in one natural phrase:

| Internal description | Possible expression |
| --- | --- |
| search large state spaces for failures and recovery paths | find failures and recovery paths in large systems |
| CP-SAT scheduling and optimization tooling | search and planning |
| robot-cell deadlock detection and recovery | robot recovery |
| simulation and evaluation infrastructure | simulation and evaluation |
| reasoning over incomplete observations | reasoning from incomplete data |

These are contextual rewrites, not automatic substitutions. Retain "deadlock", "CP-SAT" or another mechanism when that specific mechanism is the reason for writing. Compression must not broaden a narrow result into an unsupported capability.

Prefer a sentence that creates one clear mental model:

> finding failures and recovery paths in large automated systems

Over a sentence requiring the reader to assemble components:

> building systems that search large state spaces for failures and recovery paths, along with simulation and optimization tooling around them

## Choose the level for this recipient

| Reader | Useful expression when supported by current facts |
| --- | --- |
| Research scientist / ML engineer | search, planning and simulation, especially failure/recovery search under incomplete state |
| Technical executive / engineering director | search and planning systems for finding failures and recovery paths in automated systems |
| Plant / operations person | figuring out what causes automated systems to stop and how to recover them |
| Investor | building systems that detect failures and find recovery paths in robotic cells |

These are options, not mandatory introductions or title-based templates. Relationship, purpose and the supplied draft can outweigh a role-based prior. Do not manufacture different pitches for people at the same organization when the shared description already works.

## Apply it to research too

Research flow: raw facts → what they mean → what matters to this recipient → shortest natural phrase preserving that meaning.

An announcement of a "$40M modernization program involving automated sorting and new vision systems" may only need "they're expanding the automated sorting line" in the email, if the source actually establishes that expansion. Keep the amount, equipment and source in the research record. Include them in the email only when they change the reason to write.

Do not turn a planned expansion into an operating line, a hypothesis into a known failure, or a company-wide signal into a facility-specific fact. Compressing research never permits stronger claims.

## Detect implementation-shaped prose

Inspect sentences with several technical noun phrases linked by "along with", "as well as", "tooling around", "systems that", "including work on", or a long list of methods. These are review cues, not banned strings. Rewrite when the sentence describes components instead of the useful idea.

## Final compression check

For each sentence explaining Andrew's work or researched context:

1. Could a smart reader summarize this in five to ten words?
2. Would that phrase preserve the reason it matters, the useful technical detail and the thought connecting it to the email? Consider it only if the current sentence has a specific clarity problem.
3. Did the shorter version become generic or remove the interesting mechanism? If yes, restore one level of specificity.
4. Did it alter scope, confidence, causality, timing or factual meaning? If yes, repair it against the source.
5. Does it still sound like something Andrew would naturally say?

Five to ten words is a diagnostic, not a sentence limit. Do not create choppy prose or shorten every email. The goal is maximum useful information per natural sentence, not minimum word count. Preserve an already approved phrase unless current instructions or the recipient's needs justify changing it.
