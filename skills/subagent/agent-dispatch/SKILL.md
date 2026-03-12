---
name: agent-dispatch
description: Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated worktrees, branches, and tmux sessions with automatic monitoring and failure recovery.
---

# Agent Dispatch

Dispatch tasks to execution agents with isolated environments, automatic monitoring, and failure recovery.

---

## Quick Start

**Dispatch a task:**

```bash
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh <task-id> <agent> "<prompt>" [model]
```

**Example:**

```bash
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh feat-auth opencode \
  "Implement JWT authentication in src/api/auth.ts"
```

---

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `task-id` | Yes | Unique slug (e.g., `feat-auth`, `fix-login-bug`) |
| `agent` | Yes | Agent type: `opencode`, `gemini`, `codex`, `claude` |
| `prompt` | Yes | Task description (quoted) |
| `model` | No | Override default model |

---

## What spawn-agent.sh Does

1. **Creates isolated environment**
   - Git worktree at `../agent-worktrees/<task-id>`
   - New branch `agent/<task-id>`
   
2. **Sets up dependencies**
   - Runs `pnpm install` or `npm install` if `package.json` exists

3. **Starts agent session**
   - Creates tmux session `agent-<task-id>`
   - Launches agent with appropriate CLI and flags

4. **Registers task**
   - Adds to `.clawdbot/active-tasks.json`

---

## Agent Types

| Agent | CLI Command | Mode | Best For |
|-------|-------------|------|----------|
| `opencode` | `opencode run` | Default config | All code work, research, complex tasks |
| `gemini` | `gemini --yolo` | Auto-approve | Docs, writing, polishing, translation |
| `codex` | `codex exec --full-auto` | Auto-approve | Bug fixes, code review |
| `claude` | `claude --dangerously-skip-permissions -p` | Non-interactive | Frontend, fast tasks |

**Specialized Aliases:**
- `code-reviewer` → Gemini with code review skill
- `docs-writer` → Gemini with docs writing skill

---

## Monitoring

### Create Monitoring Cron Job

After dispatching, create a temporary cron job to monitor the agent:

```python
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

**Step 5: DELETE this cron job (MANDATORY - NOT OPTIONAL)**

You MUST execute this EXACT tool call when task is complete or failed:

```
Tool: cron
Action: remove
Parameters: {"action": "remove", "jobId": "<job-id-from-step-1>"}
```

**Example (replace with actual job ID):**
```
cron.remove(jobId="d037ed80-56eb-43be-a8c0-e95132b9e426")
```

**CRITICAL:**
- This is NOT optional - you MUST delete the cron job
- If you don't call cron.remove(), the monitoring job will run forever
- Execute the tool call IMMEDIATELY after reporting status
- Do NOT just say "I will delete" - you MUST actually call the tool

Use tools: cron.list, tmux, git, gh, cron.remove""",
        "model": "generic/glm-5",
        "timeoutSeconds": 120  # 2 minutes - need time to think and delete cron
    },
    delivery={"mode": "announce", "channel": "telegram", "to": "<chat-id>"}
)
```

### Important Notes

- **MANDATORY**: Agent MUST call `cron.remove()` when task completes or fails
- **NOT OPTIONAL**: Saying "I will delete" is NOT enough - must execute the tool
- **Timeout**: `timeoutSeconds: 120` gives agent enough time to think and delete
- **No Auto-Delete**: OpenClaw does not support automatic deletion based on exit codes

---

## Manual Checks (Optional)

```bash
# Check all active agents
./scripts/agent-orchestration/check-agents.sh

# Attach to a running session
tmux attach -t agent-<task-id>

# View agent logs
tmux capture-pane -t agent-<task-id> -p | tail -50
```

---

## Failure Recovery (Ralph Loop)

When monitoring detects a session ended without a PR:

1. **Triggers** `ralph-loop.sh`
2. **Analyzes** failure and gathers context
3. **Restarts** agent with added context
4. **Retries** up to 3 times
5. **Notifies** you of permanent failure if all retries exhausted

---

## Reporting to User

After dispatching, always tell the user:

1. **Task ID** - so they can follow up
2. **Agent selected** - so they know what's running
3. **Monitoring** - confirm cron job is set up and when they'll hear back

**Example:**

```
✅ Task dispatched!

Task ID: feat-auth
Agent: opencode
Branch: agent/feat-auth
Tmux: tmux attach -t agent-feat-auth
Monitoring: Every 5 minutes via cron

The agent will work on this task and report progress automatically.
```

---

## Checklist Before Dispatching

- [ ] Task is complex enough (simple queries should not spawn agents)
- [ ] Agent is selected correctly (consult dispatch table in `TOOLS.md`)
- [ ] Prompt is clear and specific (vague prompts waste agent time)
- [ ] Monitoring cron job is created (otherwise you'll lose track)

---

*Last updated: 2026-03-12*
