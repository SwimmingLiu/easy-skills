# Create

## Goal

Turn a `researched` capability gap into the smallest testable Skill draft. Establish a baseline before draft authoring so every rule answers an observed need.

## Inputs

- Require the discover decision, requirement contract, representative user requests, expected artifacts, success criteria, target hosts, and permission boundaries.
- Gather reusable source material and explicitly licensed patterns; do not copy text from a source without usable license terms.
- Define which actions require confirmation and which failures must leave the environment unchanged.

## Procedure

1. Run representative requests without the Skill. For an update, snapshot and run the old Skill. Save exact omissions, unsafe actions, wrong outputs, trigger failures, duration, and token use as baseline evidence.
2. Derive the minimum behavior needed to correct those failures. Do not add speculative workflow.
3. Choose resources by responsibility: keep routing and essential procedure in `SKILL.md`; put repeatable deterministic work in tested `scripts/`; put on-demand knowledge in `references/`; put reusable output material in `assets/`.
4. Initialize the package with the official OpenAI `skill-creator` scaffolding where available. Use a folder and frontmatter `name` that follow Agent Skills naming rules.
5. Write a trigger-oriented description and imperative body. Route substantial variants through direct references and preserve progressive disclosure.
6. Add two or three realistic evaluations from the baseline, including expected artifacts, boundaries, and prohibited actions. Prefer deterministic assertions; reserve subjective judgments for human review.
7. Run scripts on representative fixtures, run package tests and `quick_validate.py`, resolve direct references, and remove generated example material that the Skill does not use.

## Outputs

- Produce a requirement contract, baseline record, minimal Skill package, initial evaluation cases, and validation report.
- Record source attribution, assumptions, permissions, and the next review scope.

## State transition

Move `researched` to `draft` only when the baseline, package, evaluations, and structural validation are durable artifacts. Enter `needs-input` if examples or success criteria are insufficient. Never mark a new draft reviewed, evaluated, or active.

## Human gate

Ask the user to confirm before overwriting an existing package, adding dependencies, executing untrusted source code, making network or paid calls, installing the Skill, or publishing it. Keep baseline runs isolated from live systems.

## Design basis

- Apply Agent Skills metadata and directory constraints.
- Apply Anthropic `skill-creator`'s intent capture, realistic tasks, baseline comparison, and iterative feedback.
- Apply OpenAI `skill-creator`'s initialization, validation, progressive disclosure, imperative writing, and forward testing.
- Apply Superpowers `writing-skills` RED-GREEN-REFACTOR: observe failure first, add the minimum rule, then test for compliance and overfitting.

