# Evaluate

## Goal

Measure trigger behavior and task effect as separate evaluation surfaces. Prove whether the candidate improves representative outcomes against a baseline or old version.

## Inputs

- Require a reviewed Skill version, requirement contract, baseline artifacts, representative cases, target environment, and predeclared thresholds.
- Tag assertions as required, prohibited-action, or informational. Identify subjective outputs that require blinded human judgment.
- Fix inputs, files, model, tools, and environment as far as practical for paired runs.

## Procedure

1. Build trigger cases for expected requests and paraphrases, plus negative requests, near misses, and conflicting Skill descriptions. Measure recall and false activation separately.
2. Build task-effect cases for normal, boundary, failure, and pressure conditions. Include ECC `skill-comply`-style supportive, neutral, and competing instructions where sequence or optional behavior matters.
3. Run candidate and baseline in the same evaluation round. Preserve raw output, tool calls, artifacts, errors, duration, tokens, and environment metadata.
4. Use deterministic assertions for objective requirements and prohibited actions. Use blinded preference or explicit human criteria for subjective quality.
5. Run `aggregate_evals.py` with thresholds declared before inspecting results. Review pass-rate deltas, per-case results, duration and token mean and variance, prohibited actions, and unstable cases.
6. Classify failures as trigger, instruction, resource, tool, environment, or test defects. Do not count environment failure as Skill failure or rewrite thresholds after seeing results.
7. Accept only when critical assertions do not regress, prohibited high-risk actions remain zero, trigger error stays within bounds, and human blockers are resolved.

## Outputs

- Produce separate trigger and task-effect reports, paired raw runs, aggregate JSON/Markdown, human feedback, and a pass or changes-required decision.
- Record weak assertions, high-variance cases, environment failures, and the exact thresholds used.

## State transition

Move `reviewed` to `evaluated` only with reproducible evidence meeting predeclared gates. Move failures to `changes-required` with clusters and evidence. Enter `blocked` for environment failure and resume at `reviewed` after resolution.

## Human gate

Ask the user to confirm evaluations that execute untrusted code, access real credentials or data, call networks or paid models, write outside an isolated fixture, or may affect production. Confirm any manual waiver of a failed gate and record its approver and reason.

## Design basis

- Apply Agent Skills evaluation guidance by separating triggering from downstream task outcomes.
- Apply Anthropic `skill-creator`'s paired with-Skill/baseline runs, objective assertions, qualitative feedback, time, and token aggregation.
- Apply ECC `skill-comply`'s supportive, neutral, competing, and ordering scenarios without binding the core workflow to one CLI or LLM grader.
- Prefer deterministic checks and case evidence; do not claim statistical significance from a small sample.

