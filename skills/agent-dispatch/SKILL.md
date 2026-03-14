---
name: agent-dispatch
description: Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated worktrees, branches, and tmux sessions with automatic monitoring and failure recovery. Use when substantial work should be delegated to an execution agent in a target git repository instead of being done in the current turn.
---

# Agent dispatch

Use this skill when you need to hand off substantial work to an execution
agent in an isolated worktree and keep watching it until it finishes or fails.

## When to dispatch

Dispatch only when the task is large enough to benefit from a dedicated agent.
Keep simple questions, tiny edits, and one-command checks in the current turn.

Good candidates:

- Multi-file implementation or refactor work
- Longer research or code review tasks
- Work that benefits from an isolated branch and tmux session

## Repository selection rules

Select the target repository before dispatching. Do not assume every task
belongs to `/home/admin/openclaw/workspace`.

Use this priority order:

1. If the user explicitly names a project path or repository, dispatch from that repo.
2. Else if the current working directory is inside a git repo, dispatch from that repo.
3. Else fall back to `/home/admin/openclaw/workspace`.

If the task is about another project such as `/home/admin/projects/ClassPets`,
set `REPO_ROOT` explicitly when calling `spawn-agent.sh`.

## Dispatch command

Use `spawn-agent.sh` to create the worktree, branch, tmux session, and agent
process.

```bash
REPO_ROOT=/absolute/path/to/repo \
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh \
  <task-id> <agent> [model] "<prompt>"
```

Example for a non-workspace repository:

```bash
REPO_ROOT=/home/admin/projects/ClassPets \
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh \
  feat-auth opencode "Implement JWT authentication in src/api/auth.ts"
```

Example when already inside the target repo:

```bash
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh \
  fix-login codex "Fix the login redirect bug in src/auth/login.ts"
```

## Spawn parameters

These are the only positional parameters passed to `spawn-agent.sh`.

| Parameter | Required | Notes |
| --- | --- | --- |
| `task-id` | Yes | Short slug such as `feat-auth` or `fix-login-bug` |
| `agent` | Yes | `opencode`, `gemini`, `codex`, `claude`, `code-reviewer`, or `docs-writer` |
| `model` | No | Optional override inserted before the prompt |
| `prompt` | Yes | Quoted task description; always the last argument |

Environment variables supported by `spawn-agent.sh`:

| Variable | Required | Notes |
| --- | --- | --- |
| `REPO_ROOT` | No but recommended for cross-repo tasks | Absolute path to the target git repository |
| `BASE_BRANCH` | No | Overrides automatic base branch detection |
| `WORKTREE_ROOT` | No | Overrides `/home/admin/openclaw/agent-worktrees` |
| `TASK_REGISTRY` | No | Overrides task registry path |

`spawn-agent.sh` detects whether the third positional argument is `model` or `prompt`.

## Prompt handling rules

Treat prompts as arbitrary multi-line text. They may contain:

- fenced code blocks
- shell metacharacters
- quotes
- backticks
- markdown

Do not inject raw multi-line prompts directly into a shell command string.
`spawn-agent.sh` writes the prompt to a file and lets the runner script read it
inside the tmux session. Keep using that pattern. If you update the skill, do
not regress to `tmux send-keys "... \"$PROMPT\""` style injection.

## Agent selection

Pick the lightest agent that can do the work well.

| Agent | Command style | Best for |
| --- | --- | --- |
| `opencode` | `opencode run` | General code work and complex tasks |
| `gemini` | `gemini --yolo` | Docs, writing, and polishing |
| `codex` | `codex exec --full-auto` | Bug fixes and code-heavy tasks |
| `claude` | `claude -p` | Fast iteration, often frontend work |
| `code-reviewer` | Gemini wrapper | Reviews using the `code-reviewer` skill |
| `docs-writer` | Gemini wrapper | Writing using the `docs-writer` skill |

If the user already specified an agent, keep it unless there is a concrete
reason to change it.

## What the script does

`spawn-agent.sh` handles the setup end to end:

1. Resolves the target git repository.
2. Detects the base branch from the current branch or falls back to `master` or `main`.
3. Creates a worktree at `/home/admin/openclaw/agent-worktrees/<task-id>`.
4. Creates or reuses branch `agent/<task-id>`.
5. Writes the prompt to `/home/admin/openclaw/agent-worktrees/.prompts/<task-id>.txt`.
6. Installs Node dependencies when `package.json` exists.
7. Creates or reuses tmux session `agent-<task-id>`.
8. Writes a runner script into the worktree and starts the selected agent from that runner.
9. Registers the task in `/home/admin/openclaw/workspace/.clawdbot/active-tasks.json` by default.

## Monitoring

After a successful dispatch, create monitoring immediately. Monitoring is not a
parameter of `spawn-agent.sh`; it is a separate OpenClaw step that creates a
temporary cron job.

### Monitoring inputs

OpenClaw must have these values before creating the cron job:

| Parameter | Required | Notes |
| --- | --- | --- |
| `channel` | Yes | Delivery channel such as `telegram` or `discord` |
| `chat-id` | Yes | Target chat or group ID |

Do not guess these values. If either value is missing, stop and ask the user
for it before creating the cron job.

### Monitoring workflow

Create a temporary cron job that checks the task every five minutes and deletes
itself when the task is no longer active.

Use this sequence:

1. Dispatch the agent with `spawn-agent.sh`.
2. Immediately check existing cron jobs for the same five-minute schedule.
3. If no conflicting job exists, create the monitoring job on the default
   five-minute cadence.
4. If a conflicting job exists at the same reporting time, keep the five-minute
   cadence but add a 10 to 20 percent jitter before the report is sent.
5. For a five-minute cadence, that jitter is 30 to 60 seconds. A simple
   `sleep` inside the cron command is sufficient.
6. Pass `channel` and `chat-id` when creating the cron job so the monitoring
   run knows where to report.
7. Tag the cron job with `task-id` and persist the cron job ID in the dispatch
   result so cleanup is deterministic.
8. On each cron run, inspect task state.
9. If the task is still running, send a short progress report and keep the cron
   job.
10. If the task is complete, send the completion report and remove the cron
   job in the same monitoring turn.
11. If the task failed or monitoring itself failed, send the failure report,
   remove the cron job, and ask the user how to proceed.

Use [scripts/monitor-agent.py](/home/admin/.agents/skills/agent-dispatch/scripts/monitor-agent.py)
as the deterministic status probe for the cron job. The script returns:

- `0`: still running
- `1`: complete, remove the temporary cron job
- `2`: failed, remove the temporary cron job and escalate to the user
- `3`: monitoring error, remove the temporary cron job and escalate to the user

The script does not send notifications by itself. OpenClaw owns delivery,
`cron.add(...)`, and `cron.remove(...)`.

### Monitoring rules

The monitoring agent must call `cron.remove()` itself when the task is complete
or failed. Reporting that it "will delete" the job is not enough.

Keep these defaults unless the caller has a reason to change them:

- Schedule: every 5 minutes
- Timeout: 120 seconds for each monitoring turn
- Delivery mode: `announce`
- Model: a low-cost general model is sufficient

When a schedule collision exists, keep the cadence at five minutes and only
shift the delivery time by 30 to 60 seconds. Do not silently change the
interval to six minutes or another cadence.

## Failure handling

Stop at the first hard failure and report it immediately. Do not continue
silently.

Always include:

- The failed step
- The exact error message
- The `task-id`
- The selected agent, if relevant
- The concrete next action or retry option

Typical hard failures:

- `spawn-agent.sh` exits non-zero
- Target repo detection fails
- Worktree or branch creation fails
- Tmux session creation fails
- Agent CLI startup fails
- Monitoring cron creation fails

Every failure report must also ask the user for a decision. Offer a concrete
next action such as:

- Retry the failed step
- Continue without monitoring
- Cancel the dispatch
- Trigger Ralph Loop manually

If monitoring detects that the session exited without a PR or commits, treat it
as a failed run, report it immediately, and wait for user feedback before
retrying or handing off to Ralph Loop.

## User report

After dispatching, send one concise status report to the user. Include the
minimum information they need to continue working with the task:

- Dispatch result: success or failure
- `task-id`
- Agent name
- Repo root
- Base branch
- Worktree path
- Branch name
- Prompt file path when useful for debugging
- Tmux session name
- Monitoring status and cron job ID, if created
- Monitoring delivery target: `channel` and `chat-id`
- One or two manual follow-up commands when useful

## Manual checks

Use these commands when you need to inspect a running or finished task.

```bash
./scripts/agent-orchestration/check-agents.sh
tmux attach -t agent-<task-id>
tmux capture-pane -t agent-<task-id> -p | tail -50
```
