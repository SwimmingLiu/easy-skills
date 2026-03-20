---
name: agent-dispatch
description: Dispatch substantial work to agent skills through isolated worktrees, branches, tmux sessions, and monitoring. Use when a task should be handed off instead of being completed inline.
---

# Agent dispatch

Use this skill to dispatch substantial work into an isolated execution flow.

## What this skill does

This skill is responsible for:

- deciding whether a task should be dispatched,
- selecting the right agent skill,
- selecting the target repository,
- creating worktrees and branches,
- starting tmux-managed sessions,
- creating and cleaning up monitoring jobs,
- reporting dispatch status to the user.

## What this skill dispatches to

Dispatch should target an **agent skill**, not a raw agent CLI command.

Examples of agent skills available in the environment:

- `codex`
- `gemini`
- `opencode`

These skills may themselves be implemented as deterministic one-shot wrappers
around their underlying CLIs. Do not assume they provide an interactive TUI
session unless the target skill explicitly says so. For Gemini specifically,
prefer the skill wrapper script over calling the raw Gemini CLI directly from
agent-dispatch.

Task skills such as `docs-writer` and `code-reviewer` are not dispatch targets
by themselves. They define task methodology, not the execution backend.

## Task skills are optional

A dispatched task does **not** need to use a task skill.

Use a task skill only when the task benefits from specialized workflow or
standards.

Examples:

- `gemini` + `docs-writer` for documentation work
- `codex` + `code-reviewer` for code review work
- `codex` alone for generic implementation work
- `opencode` alone for general execution work
- `gemini` alone for open-ended reasoning work

Do not force every dispatched task into a composition model.

## Repository selection

Select the target repository before dispatching.

1. Use the repository explicitly named by the user, if any.
2. Otherwise use the current git repository, if the current directory is inside one.
3. Otherwise fall back to the current OpenClaw workspace only when workspace
   fallback has been explicitly acknowledged.

Do not hardcode machine-specific absolute paths or usernames in this skill.
Resolve repository and workspace paths dynamically from the current runtime
context.

## Dispatch command

Use the environment's agent orchestration entrypoint to create the worktree,
branch, tmux session, and agent process.

Example shape:

```bash
REPO_ROOT=/absolute/path/to/repo \
$OPENCLAW_WORKSPACE/scripts/agent-orchestration/spawn-agent.sh \
  <task-id> <agent-skill> [model] "<prompt>"
```

The exact workspace root should be resolved dynamically by the environment.
Do not assume a fixed path such as `/home/admin/...`.

The caller should dispatch to an agent skill. The agent skill then defines how
the underlying tool is launched.

## Selection guidance

Pick the lightest suitable agent skill for the task.

- `opencode`: general implementation and broad execution work via deterministic one-shot automation
- `gemini`: writing, analysis, and reasoning work via deterministic one-shot automation
- `codex`: code analysis, refactoring, and review-heavy work via deterministic one-shot automation

Add a task skill only when it clearly helps.

## Monitoring

After dispatch succeeds, create monitoring immediately.

Monitoring is separate from the spawn step. Use a temporary cron job to check
status every five minutes and remove itself on completion or failure.

## Failure handling

Stop on the first hard failure and report:

- failed step,
- exact error,
- task ID,
- selected agent skill,
- next action or retry option.

## User report

After dispatching, report:

- success or failure,
- task ID,
- selected agent skill,
- repo root,
- base branch,
- worktree path,
- branch name,
- tmux session,
- monitoring status.
