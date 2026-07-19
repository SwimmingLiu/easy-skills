---
name: skill-lifecycle
description: Use when discovering, creating, reviewing, evaluating, optimizing, or maintaining Agent Skills with evidence-backed decisions.
---

# Skill Lifecycle

Manage a Skill as a stateful, evidence-backed artifact. Read [the evidence contract](references/evidence-schema.md). Read exactly one operation guide before acting. Complete that operation, record its report and state, and route again only when the result requires another operation.

## Core rules

1. Identify the current state, requested outcome, available evidence, and possible side effects.
2. Keep discovery, creation, review, evaluation, optimization, and maintenance as separate operations. Do not silently turn an assessment into a modification.
3. Treat review and discovery as read-only. Before any write, install, deletion, publication, network submission, paid call, or permission expansion, present the action and obtain explicit confirmation.
4. Advance state only with durable evidence. Record assumptions as assumptions; never infer success from file existence, popularity, mtime, or missing telemetry.
5. Emit the shared operation report fields: state, findings, gates, artifacts, evidence, decision, and next operation. Use the templates in `assets/report-templates/` when writing durable reports.
6. Use the supplied scripts for deterministic inventory, validation, lifecycle state, and evaluation aggregation. Run each script with `--help` before first use.

## Quick reference

| User need | Operation | Read | Typical state result |
| --- | --- | --- | --- |
| Find, compare, reuse, fork, or combine Skills | discover | [Discover](references/discover.md) | `intake` to `researched` |
| Build a missing Skill after discovery | create | [Create](references/create.md) | `researched` to `draft` |
| Inspect quality, safety, triggering, or structure | review | [Review](references/review.md) | `draft` to `reviewed` or `changes-required` |
| Measure triggering or task outcomes | evaluate | [Evaluate](references/evaluate.md) | `reviewed` to `evaluated` or `changes-required` |
| Change a Skill from observed failures | optimize | [Optimize](references/optimize.md) | `changes-required` to a new `draft` |
| Inventory, update, merge, or retire managed Skills | maintain | [Maintain](references/maintain.md) | `active` remains active, changes, or retires |

## Routing flow

Use these decisions in order:

1. If creation is requested but no candidate search and gap decision exist, run `discover`; do not start `create` yet.
2. If the user asks to inspect and fix, run `review` read-only, report findings and a plan, then stop at the confirmation gate. Route a confirmed change to `optimize`.
3. If the question is whether a Skill works, run `evaluate`; do not substitute static review for execution evidence.
4. If a failure is already supported by review or evaluation evidence, run `optimize`; do not reopen creation from scratch.
5. If the request concerns installed or published Skills as a collection, versions, drift, overlap, updates, or retirement, run `maintain`.
6. Otherwise select the single row in Quick reference that matches the requested outcome. On missing decisive input, enter `needs-input`; on an external failure, enter `blocked` and preserve the resume state.

## Example

User: "Review this upload Skill and improve anything unsafe."

Route first to `review`. Read the package without executing or editing it, separate trigger findings from task and safety findings, and report severity, evidence, and a proposed change plan. Ask for confirmation before editing. After confirmation, route to `optimize`, snapshot the current version, make the smallest evidence-backed change, rerun affected review and evaluation gates, and roll back if the candidate regresses. Never upload findings or install dependencies unless separately confirmed.

## Common mistakes

| Mistake | Correction |
| --- | --- |
| Creating before checking existing Skills | Run `discover` and decide use, fork, compose, or create. |
| Calling a clean static scan proof of effectiveness | Run trigger and task-effect evaluation separately. |
| Editing during review | Report facts and a plan; wait for confirmation before `optimize`. |
| Rewriting the whole Skill after one failure | Change the smallest implicated surface and rerun regression gates. |
| Treating Stars, mtime, or absent logs as quality or usage | Record them only as weak signals and preserve unknowns. |
| Advancing state without artifacts | Keep the current state and attach durable evidence first. |
| Performing a side effect because the user asked for a broad outcome | Name the exact side effect and obtain explicit confirmation. |
