# Optimize

## Goal

Make the minimal evidence-driven change that addresses a verified failure while preserving established behavior and a reliable rollback path.

## Inputs

- Require review findings or failed evaluation cases, the implicated version hash, current gates, and accepted success and regression thresholds.
- Separate Skill defects from environment and test defects before proposing changes.
- Identify the smallest implicated surface: description, procedure, reference routing, script, asset, dependency, or evaluation.

## Procedure

1. Cluster failures by cause and link each cluster to raw evidence. Reject optimization requests based only on taste, Stars, or hypothetical improvement.
2. Propose one minimal change per cluster with predicted benefit, possible regressions, affected gates, and an explicit modification plan.
3. Present the plan and obtain confirmation before mutation. Save the current content hash, version snapshot, artifacts, and rollback command or restoration method.
4. Modify only the implicated surface. Avoid test-phrase hardcoding and broad rewrites.
5. Run affected tests first, then full trigger, task-effect, safety, compatibility, and package regressions. Use a held-out set when the benchmark is stable enough.
6. Compare quality, false triggers, prohibited actions, duration, tokens, variance, and human feedback against predeclared thresholds.
7. Accept the candidate only if every required gate passes. On regression, restore the prior files using version control or backup, record a lifecycle rollback event, and verify the restored state.

## Outputs

- Produce a chain from failure evidence to plan, confirmed change, before/after hashes, verification results, and accept or rollback decision.
- Record which review and evaluation gates must run again and any remaining uncertainty.

## State transition

Move `changes-required` to a new `draft`; require affected review and evaluation gates again. Do not restore `reviewed` or `evaluated` merely because files changed. Record `rolled-back` as an event while restoring the prior persistent state after a rejected candidate.

## Human gate

Ask the user to confirm every file modification and separately confirm dependency, permission, network, paid, installation, deletion, publication, or production action. Automatic acceptance is limited to low-risk changes with predeclared thresholds and a tested rollback path.

## Design basis

- Apply `skill-optimizer`'s plan, confirm, modify, and verify loop.
- Apply Anthropic `skill-creator`'s evidence-based generalization, concise prompts, explanation of non-obvious rules, and extraction of repeated deterministic work.
- Apply Superpowers `writing-skills` regression and anti-overfitting discipline.
- Reserve Microsoft SkillOpt rollout, reflection, candidate selection, and held-out validation for stable benchmarks; do not auto-accept generated changes in the first version.
