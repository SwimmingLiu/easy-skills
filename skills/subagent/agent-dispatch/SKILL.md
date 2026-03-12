---
name: agent-dispatch
description: Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated worktrees, branches, and tmux sessions. Handles the full lifecycle including monitoring and failure recovery.
---

# Agent dispatch

This skill encapsulates the full workflow for dispatching tasks to execution
agents. OpenClaw calls this skill whenever it needs to start an agent.

## Dispatch command

Run `spawn-agent.sh` from the workspace root to create an isolated environment
and start the agent:

```bash
# Use absolute path (recommended)
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh <task-id> <agent> "<prompt>" [model]

# Or use relative path from workspace
cd /home/admin/openclaw/workspace && ./scripts/agent-orchestration/spawn-agent.sh <task-id> <agent> "<prompt>" [model]
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `task-id` | Yes | Unique slug for the task (for example, `feat-auth`, `fix-login-bug`) |
| `agent` | Yes | Agent type: `opencode`, `gemini`, `codex`, or `claude` |
| `prompt` | Yes | The task prompt, quoted |
| `model` | No | Override the default model for this agent |

**Example:**

```bash
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh feat-auth opencode \
  "Implement JWT authentication in src/api/auth.ts"
```

## What spawn-agent.sh does

1. Creates a git worktree at `../agent-worktrees/<task-id>` on a new branch
   `agent/<task-id>`.
2. Runs `pnpm install` (or `npm install`) if `package.json` exists.
3. Creates a tmux session named `agent-<task-id>` in the worktree directory.
4. Starts the agent with the appropriate CLI command and flags.
5. Registers the task in `.clawdbot/active-tasks.json`.

## Agent types and CLI flags

| Agent | CLI command | Mode | Best for |
|-------|-------------|------|----------|
| `opencode` | `opencode run` | Default config | All code work, research, complex tasks |
| `gemini` | `gemini --yolo` | Auto-approve | Docs, writing, polishing, translation |
| `codex` | `codex exec --full-auto` | Auto-approve | Bug fixes, code review |
| `claude` | `claude --dangerously-skip-permissions -p` | Non-interactive | Frontend, fast tasks |

Specialized aliases `code-reviewer` and `docs-writer` start Gemini with the
corresponding skill pre-loaded in the prompt.

## Monitoring

After dispatching a task, create a temporary cron job to monitor the agent
automatically. The cron job runs `scripts/monitor-agent.py` every 5–10 minutes,
reports progress via `announce` delivery, and deletes itself when the task
completes (session ends or PR is created).

**Create a monitoring cron job:**

```python
# Use OpenClaw's cron tool to register a temporary monitoring job
cron.create(
    id=f"monitor-{task_id}",
    schedule="*/5 * * * *",   # every 5 minutes
    command=f"python3 scripts/agent-orchestration/monitor-agent.py {task_id}",
    auto_delete_when="task_complete",  # removes itself on completion
    deliver_via="announce",            # reports progress to the user
)
```

`monitor-agent.py` checks whether the tmux session is alive, captures recent
output, checks for new commits, and returns structured status. When it detects
completion (session exited or PR created), it signals `task_complete` so the
cron job removes itself.

**Fallback — manual checks (optional):**

```bash
# Check all active agents
./scripts/agent-orchestration/check-agents.sh

# Attach to a running session
tmux attach -t agent-<task-id>
```

## Reporting to the user

After running `spawn-agent.sh` and creating the monitoring cron job, always
tell the user:

- **Task ID** — so they can follow up.
- **Agent selected** — so they know what's running.
- **Monitoring** — confirm the cron job is set up and when they'll hear back.

## Failure recovery (Ralph Loop)

When the monitoring cron job detects that a session ended without a PR, it
triggers `ralph-loop.sh`, which analyzes the failure and restarts the agent
with added context. It retries up to three times before notifying you of a
permanent failure.
