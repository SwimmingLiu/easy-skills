---
name: code-reviewer
description: Review code changes for correctness, maintainability, security, edge cases, and project standards. Use when the task is code review for local changes, staged diffs, working tree changes, or remote Pull Requests.
---

# Code reviewer

Use this skill when the task itself is code review.

This skill defines review workflow, review standards, and review output
structure. It is not an execution-agent skill.

## Review target

Determine the review target first:

- **Remote PR**: when the user provides a PR number or URL.
- **Local changes**: when the user asks to review current changes, staged
  changes, or working tree changes.

## Preparation

### Remote PRs

1. Check out the PR.
2. Read the PR description and discussion.
3. Run project verification when appropriate.
4. Inspect changed files and surrounding code.

### Local changes

1. Inspect `git status`.
2. Read `git diff` and `git diff --staged` as needed.
3. Run verification when the scope is large enough to justify it.

## Review pillars

Evaluate changes across these dimensions:

- **Correctness**
- **Maintainability**
- **Readability**
- **Efficiency**
- **Security**
- **Edge cases and error handling**
- **Testability**

## Feedback structure

Use this structure when reporting results:

1. **Summary**
2. **Critical findings**
3. **Improvements**
4. **Nitpicks**
5. **Conclusion**

## Tone

Be constructive, direct, and professional.

- Explain why an issue matters.
- Prefer actionable suggestions over vague criticism.
- Acknowledge good decisions when appropriate.
