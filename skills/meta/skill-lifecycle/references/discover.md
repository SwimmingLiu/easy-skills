# Discover

## Goal

Decide whether to **use**, **fork**, **compose**, or **create** a Skill. Complete discovery before create so a new package represents a verified capability gap rather than duplication.

## Inputs

- Capture the user goal, representative requests, expected artifacts, success criteria, target hosts, permissions, and license constraints.
- Accept local Skill roots and user-supplied GitHub or X/Twitter leads. Treat social posts and Stars as discovery or ranking signals, not proof.
- Record constraints that would reject a candidate, including incompatible licenses, untrusted dependencies, or prohibited side effects.

## Procedure

1. Convert the request into a capability matrix: triggers, task steps, inputs, outputs, tools, permissions, risks, and acceptance criteria.
2. Run `inventory_skills.py` against approved roots. Discover only files named `SKILL.md`; record name, source, ref, path, content hash, license, and hosts.
3. Search local and official sources first, then maintained repositories and user-provided GitHub/X leads. Do not install candidates during discovery.
4. Inspect each candidate's actual `SKILL.md`, direct references, scripts, tests, license, network behavior, commands, writes, credentials, and install path. Do not decide from README or Stars alone.
5. Create one evidence card per candidate. Mark unverifiable claims and missing licenses as unknown.
6. Compare capability coverage, trust, compatibility, risk, adaptation cost, and reproducibility.
7. Select `use` for an adequate candidate, `fork` for one coherent candidate needing bounded changes, `compose` for complementary Skills with clear boundaries, or `create` only for a remaining gap.

## Outputs

- Produce the requirement matrix and candidate evidence cards.
- Record rejected candidates and reasons.
- Record one selected decision: use, fork, compose, or create, with evidence references and remaining risks.

## State transition

Move `intake` to `researched` only after recording sources, licenses, compatibility, risk, and the selected decision. Enter `needs-input` when missing goals or constraints would change the decision. Stop when use, fork, or compose already meets the goal.

## Human gate

Keep discovery read-only. Ask the user to confirm before installing, cloning into a managed location, writing a fork, calling a paid service, sending content over the network, or accepting an unknown license or risk.

## Design basis

- Apply ECC `skill-scout`'s local-first discovery and command, write, network, and credential inspection.
- Apply Vercel Skills CLI's reproducible source/ref/path/hash identity.
- Apply Agent Skills structure and metadata as the unit of inspection.
- Add compose, licensing, host compatibility, and supply-chain evidence; use Stars only to prioritize inspection.
