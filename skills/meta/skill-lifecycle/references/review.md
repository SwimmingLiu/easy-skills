# Review

## Goal

Inspect a Skill read-only and produce evidence-backed findings and a change plan. Keep review separate from modification so the reported evidence remains a valid pre-change baseline.

## Inputs

- Fix the package path, target hosts, expected behavior, review scope, and accepted risk policy.
- Read `SKILL.md`, its direct references, scripts, assets used by the workflow, evaluations, license, and dependency manifests.
- Obtain neighboring Skill descriptions when checking trigger overlap.

## Procedure

1. Record the reviewed version or content hash. Do not execute, install, edit, format, or upload the package.
2. Run `validate_skill.py` and inspect frontmatter, naming, local links, resource routing, unused material, and host compatibility.
3. Review trigger behavior independently: test positive requests, paraphrases, negative requests, near misses, and overlap with adjacent Skills.
4. Review task design independently: trace inputs, normal flow, missing inputs, empty results, partial success, timeouts, authentication failures, recovery, and output contracts.
5. Inspect scripts and instructions for network access, credentials, writes, deletion, installation, paid calls, privilege changes, prompt injection, and license or supply-chain risks. Treat scanners as evidence, not certification.
6. Classify each finding as Blocker, High, Medium, or Low. Include file and line, evidence, impact, remediation, and the gate to rerun.
7. Summarize accepted risks and produce a bounded modification plan. Stop before editing and request confirmation.

## Outputs

- Produce a versioned review report, structured findings, gate results, accepted-risk record, and proposed modification plan.
- Distinguish observed facts, tool findings, inferences, and assumptions.

## State transition

Move `draft` to `reviewed` only when no unresolved Blocker or High finding remains and accepted risks are recorded. Otherwise move to `changes-required` with evidence and named rerun gates. A clean review does not imply `evaluated`.

## Human gate

Review is read-only. Ask the user to confirm the modification plan before routing to `optimize` or changing any file. Separately confirm execution, dependency installation, network submission, deletion, publication, paid calls, or permission expansion.

## Design basis

- Apply `chujianyun/skill-optimizer`'s Scope -> Review -> Plan -> Confirm -> Modify -> Verify boundary and its trigger, failure-path, resource, dependency, safety, and side-effect checks.
- Apply Cisco Skill Scanner's static, data-flow, trigger-overlap, SARIF, and CI evidence as the primary external scanning model.
- Use NVIDIA SkillSpector as an independent strict-path cross-check, while retaining human inspection of privileged paths.
- Do not treat zero scanner findings or an unbenchmarked optimizer claim as proof of safety or task quality.
