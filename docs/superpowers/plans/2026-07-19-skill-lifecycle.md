# Skill Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an installable `skill-lifecycle` Skill that routes discover, create, review, evaluate, optimize, and maintain operations through explicit states, evidence, gates, reports, and rollback-safe tools.

**Architecture:** Keep `SKILL.md` as a compact router and place each operation's judgment-heavy procedure in a direct reference file. Implement deterministic inventory, validation, state transitions, and evaluation aggregation as dependency-free Python CLIs. Persist a versioned `lifecycle.json` and emit Markdown reports so both agents and humans can audit every decision.

**Tech Stack:** Agent Skills Markdown/YAML, Python 3 standard library, `unittest`, JSON, Markdown templates.

---

## File Map

- `skills/meta/skill-lifecycle/SKILL.md`: trigger metadata, routing rules, shared gates, and output contract.
- `skills/meta/skill-lifecycle/agents/openai.yaml`: Codex UI metadata.
- `skills/meta/skill-lifecycle/references/*.md`: six operation guides plus the state/evidence schema.
- `skills/meta/skill-lifecycle/scripts/lifecycle_common.py`: shared JSON, hashing, path, and report helpers.
- `skills/meta/skill-lifecycle/scripts/inventory_skills.py`: strict `SKILL.md` discovery and content-hash inventory.
- `skills/meta/skill-lifecycle/scripts/validate_skill.py`: structure, frontmatter, references, risk, and placeholder checks.
- `skills/meta/skill-lifecycle/scripts/update_lifecycle.py`: guarded state transitions, run history, gates, and rollback records.
- `skills/meta/skill-lifecycle/scripts/aggregate_evals.py`: with/baseline aggregation and regression decisions.
- `skills/meta/skill-lifecycle/assets/report-templates/*.md`: reusable evidence-card and operation-report shapes.
- `skills/meta/skill-lifecycle/evals/evals.json`: realistic routing and behavior evaluations.
- `skills/meta/skill-lifecycle/tests/test_*.py`: unit, CLI, package, and integration tests.
- `README.md`: discoverability and installation example for the new Skill.

### Task 1: Record the RED baseline

**Files:**
- Create: `docs/superpowers/evals/skill-lifecycle-baseline.md`
- Create: `docs/superpowers/evals/skill-lifecycle-evals.json`

- [x] Run three fresh agents without the Skill against: pressured creation without discovery/tests; immediate mutation during review; retirement based only on mtime/read logs.
- [x] Save each prompt, the observed response, and concrete failures such as skipped discovery, missing state/evidence, conflated review/optimization, or unsafe retirement.
- [x] Encode the same prompts in the baseline eval JSON with expected outcomes and behavior tags.
- [x] Verify the observations contain raw evidence rather than an invented summary.

### Task 2: Scaffold and package contract

**Files:**
- Create: `skills/meta/skill-lifecycle/tests/test_package.py`
- Create: `skills/meta/skill-lifecycle/SKILL.md`
- Create: `skills/meta/skill-lifecycle/agents/openai.yaml`
- Create: `skills/meta/skill-lifecycle/references/*.md`
- Create: `skills/meta/skill-lifecycle/scripts/*.py`
- Create: `skills/meta/skill-lifecycle/assets/report-templates/*.md`
- Create: `skills/meta/skill-lifecycle/evals/baseline-observations.md`
- Create: `skills/meta/skill-lifecycle/evals/evals.json`

- [x] Write `test_package.py` first. Assert the folder name and frontmatter name are `skill-lifecycle`, description starts with `Use when`, only `name` and `description` appear in frontmatter, every direct reference exists, `agents/openai.yaml` names `$skill-lifecycle`, and no placeholder tokens remain.
- [x] Run `python -m unittest skills/meta/skill-lifecycle/tests/test_package.py -v`; expect failure because the package does not exist.
- [x] Run the official `init_skill.py skill-lifecycle --path skills/meta --resources scripts,references,assets` with interface values `Skill Lifecycle`, `Create, review, evaluate, optimize, and maintain Agent Skills`, and `Use $skill-lifecycle to review this Skill and plan evidence-backed improvements.`
- [x] Replace generated placeholders with the minimal router and direct reference links required by the package test.
- [x] Copy the recorded RED evidence and scenarios into the Skill's `evals/` directory after initialization.
- [x] Run the package test and official `quick_validate.py`; expect both to pass.

### Task 3: Guarded lifecycle state engine

**Files:**
- Create: `skills/meta/skill-lifecycle/tests/test_update_lifecycle.py`
- Create: `skills/meta/skill-lifecycle/scripts/lifecycle_common.py`
- Create: `skills/meta/skill-lifecycle/scripts/update_lifecycle.py`
- Create: `skills/meta/skill-lifecycle/references/evidence-schema.md`

- [x] Write failing tests for initialization at `intake`, legal `intake -> researched`, rejection of illegal transitions, required evidence on maturity transitions, exception-state resume, operation history, and atomic rollback-safe writes.
- [x] Run `python -m unittest skills/meta/skill-lifecycle/tests/test_update_lifecycle.py -v`; expect import or behavior failures.
- [x] Implement a CLI with `init`, `transition`, `show`, and `rollback` subcommands. Store `schema_version`, `skill`, `state`, `resume_state`, `version`, `runs`, `gates`, and `artifacts`.
- [x] Require at least one evidence reference for `researched`, `draft`, `reviewed`, `evaluated`, `release-ready`, `active`, and `retired`; require `--confirm` for `active`, `retired`, and rollback.
- [x] Write via a sibling temporary file and `os.replace`; preserve the previous state when entering `needs-input` or `blocked`.
- [x] Run the focused tests, then all lifecycle tests; expect pass.

### Task 4: Inventory and static review tools

**Files:**
- Create: `skills/meta/skill-lifecycle/tests/test_inventory_skills.py`
- Create: `skills/meta/skill-lifecycle/tests/test_validate_skill.py`
- Create: `skills/meta/skill-lifecycle/scripts/inventory_skills.py`
- Create: `skills/meta/skill-lifecycle/scripts/validate_skill.py`

- [x] Write failing inventory tests proving only files named `SKILL.md` are discovered, dot/cache directories are ignored, SHA-256 changes with content, and JSON contains name/path/source/ref/license/hosts.
- [x] Implement deterministic sorted inventory with `--root`, `--output`, optional source/ref/license/host metadata, and Markdown summary output.
- [x] Write failing validator tests for malformed frontmatter, invalid names, broken local references, placeholders, undisclosed risky commands, and a clean package.
- [x] Implement structured findings with `severity`, `code`, `message`, `path`, and `line`; return exit 0 without Blocker/High findings and exit 1 otherwise.
- [x] Run focused and combined tests; expect pass with no warnings.

### Task 5: Evaluation aggregation and regression gate

**Files:**
- Create: `skills/meta/skill-lifecycle/tests/test_aggregate_evals.py`
- Create: `skills/meta/skill-lifecycle/scripts/aggregate_evals.py`
- Create: `skills/meta/skill-lifecycle/references/evaluate.md`
- Create: `skills/meta/skill-lifecycle/references/optimize.md`

- [x] Write failing tests for pass-rate mean, duration/token mean and population standard deviation, per-case deltas, missing-pair rejection, predeclared thresholds, and regression decisions.
- [x] Define input records with `case_id`, `variant`, `assertions`, `duration_ms`, and `total_tokens`; variants must pair `candidate` with `baseline`.
- [x] Implement JSON and Markdown output. Mark `accepted` only when pass-rate delta meets threshold, prohibited-action failures are zero, and optional time/token regression limits pass.
- [x] Run focused tests and a CLI fixture; expect deterministic output and correct exit status.

### Task 6: Complete six operation guides and templates

**Files:**
- Modify: `skills/meta/skill-lifecycle/SKILL.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/discover.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/create.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/review.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/evaluate.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/optimize.md`
- Create/Modify: `skills/meta/skill-lifecycle/references/maintain.md`
- Create: `skills/meta/skill-lifecycle/assets/report-templates/evidence-card.md`
- Create: `skills/meta/skill-lifecycle/assets/report-templates/operation-report.md`

- [x] Extend package tests to assert every guide contains Goal, Inputs, Procedure, Outputs, State transition, Human gate, and Design basis sections.
- [x] Run the package test; expect failure for missing sections.
- [x] Write the six guides using imperative language and the design's exact boundaries: discover before create, review before mutation, trigger/effect separation, evidence-driven minimal optimization, hash-based maintenance, and explicit side-effect confirmation.
- [x] Keep `SKILL.md` under 500 lines and route directly to one relevant guide. Add a quick-reference table, non-obvious routing flow, one concrete example, and common mistakes.
- [x] Add report templates that require state, findings, gates, artifacts, evidence, decision, and next operation.
- [x] Run package, validator, and placeholder tests; expect pass.

### Task 7: End-to-end workflow and repository integration

**Files:**
- Create: `skills/meta/skill-lifecycle/tests/test_workflow.py`
- Modify: `README.md`

- [x] Write a failing integration test that inventories a fixture Skill, validates it, initializes lifecycle state, transitions with evidence through researched/draft/reviewed/evaluated/release-ready, records a failed candidate, and verifies rollback/decision output.
- [x] Run the integration test; expect failure at the first unsupported contract.
- [x] Make only the minimal cross-script changes needed for the complete workflow.
- [x] Add `skill-lifecycle` to README under a Meta Skills section with local and GitHub installation commands.
- [x] Run `python -m unittest discover -s skills/meta/skill-lifecycle/tests -v`, `quick_validate.py`, all four CLIs with `--help`, and a temporary end-to-end workspace; expect pass.

### Task 8: Forward-test and deployment verification

**Files:**
- Modify: `skills/meta/skill-lifecycle/evals/baseline-observations.md`
- Modify as evidence requires: `skills/meta/skill-lifecycle/SKILL.md`, `references/*.md`, tests.

- [x] Run fresh agents with the completed Skill against all three baseline prompts and one variation prompt. Save outputs separately from baseline evidence.
- [x] Compare behavior against expected outcomes without leaking the intended answer to agents. Record new gaps and fix them with a failing package/behavior test first.
- [x] Re-run forward tests after any revision; require discover/create/review/evaluate/optimize/maintain routing, explicit state/evidence, and no unconfirmed side effects.
- [x] Install from the local directory using `npx skills add ./skills/meta/skill-lifecycle -g -y` only in an isolated temporary HOME or use the CLI's non-global dry mechanism; verify discovery without changing the user's live installation.
- [x] Run the full unit suite, official validator, placeholder scan, `git diff --check`, and requirement-by-requirement audit against the design document.
