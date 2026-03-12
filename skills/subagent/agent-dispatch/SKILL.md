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
automatically. The cron job runs every 5–10 minutes, checks the agent status,
reports progress via `announce` delivery, and **deletes itself when the task
completes**.

**Create a monitoring cron job:**

```python
# Use OpenClaw's cron tool to register a temporary monitoring job
cron.add(
    name=f"Monitor {task_id}",
    sessionTarget="isolated",
    schedule={"kind": "every", "everyMs": 300000},  # 5 minutes
    payload={
        "kind": "agentTurn",
        "message": f"""Check the status of task {task_id} and AUTO-DELETE this cron job when complete.

**CRITICAL: You MUST read this entire prompt before starting.**

Your goal: Check if task {task_id} is complete, and if so, DELETE this cron job.

**Step 1: Get this cron job's ID**
- Call: cron.list()
- Find the job with name="Monitor {task_id}"
- Remember the job ID (you'll need it to delete)

**Step 2: Check if tmux session is running**
- Run: tmux list-sessions | grep agent-{task_id}
- If session exists, task is still running
- Report progress and STOP (do NOT delete cron yet)

**Step 3: If session NOT running, check completion**
- Check for new commits: cd /home/admin/openclaw/workspace/../agent-worktrees/{task_id} && git log --oneline -5
- Check for PR: gh pr view agent/{task_id} --json url 2>/dev/null || echo "No PR"

**Step 4: Decide what to do**
- If PR exists → Task COMPLETE
- If session ended with new commits → Task COMPLETE (check manually)
- If session ended without commits → Task FAILED

**Step 5: DELETE this cron job (REQUIRED for complete/failed tasks)**
- You MUST call: cron.remove(jobId="<the-job-id-from-step-1>")
- Report completion/failure status to user
- This cleanup is REQUIRED

Use tools: cron.list, tmux, git, gh, cron.remove""",
        "model": "generic/glm-5",
        "timeoutSeconds": 120  # 2 minutes - need time to think and delete cron
    },
    delivery={"mode": "announce", "channel": "telegram", "to": "<chat-id>"}
)
```

**Important:** 
- The monitoring agent must explicitly call `cron.remove(jobId="<job-id>")` when task completes or fails
- `timeoutSeconds: 120` gives the agent enough time to think and delete the cron job
- OpenClaw does not support automatic deletion based on exit codes

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
