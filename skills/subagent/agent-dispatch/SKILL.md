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
| `channel` | Yes | Channel for monitoring reports (e.g., `telegram`, `discord`) |
| `chat-id` | Yes | Chat/Group ID for delivery (e.g., `-5247534845`) |

**Important:** `channel` and `chat-id` are **REQUIRED** parameters. OpenClaw MUST provide these when calling the skill.

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
        "model": "generic/glm-5"
    },
    timeoutSeconds=120,  # 2 minutes - job level timeout (outside payload)
    delivery={"mode": "announce", "channel": channel, "to": chat-id}
)
```

### Important Notes

- **MANDATORY**: Agent MUST call `cron.remove()` when task completes or fails
- **NOT OPTIONAL**: Saying "I will delete" is NOT enough - must execute the tool
- **Timeout**: `timeoutSeconds=120` at job level (not inside payload) gives agent enough time to think and delete
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

## Error Handling and Mandatory Reporting

**CRITICAL: OpenClaw MUST report errors IMMEDIATELY at ANY step.**

### Mandatory Error Reporting Points

**1. Spawn Agent Failure**
```
❌ ERROR: Failed to spawn agent

- Step: spawn-agent.sh execution
- Error: [exact error message]
- Task ID: [task-id]
- Agent: [agent type]

Action required: Check tmux session, worktree, or agent availability
```

**2. Worktree Creation Failure**
```
❌ ERROR: Failed to create worktree

- Step: git worktree creation
- Error: [exact error message]
- Path: ../agent-worktrees/[task-id]

Action required: Check disk space, permissions, or git conflicts
```

**3. Branch Creation Failure**
```
❌ ERROR: Failed to create branch

- Step: git branch creation
- Error: [exact error message]
- Branch: agent/[task-id]

Action required: Check if branch already exists or git conflicts
```

**4. Cron Job Creation Failure**
```
❌ ERROR: Failed to create monitoring cron job

- Step: cron.add()
- Error: [exact error message]
- Task ID: [task-id]

Action required: Manual monitoring needed. Check cron service status.
```

**5. Agent Startup Failure**
```
❌ ERROR: Agent failed to start

- Step: Agent CLI execution
- Error: [exact error message]
- Tmux: agent-[task-id]

Action required: Check agent installation, permissions, or logs
```

### Error Response Protocol

**When ANY error occurs:**

1. **STOP** immediately
2. **REPORT** error to user with:
   - Which step failed
   - Exact error message
   - Task ID
   - Suggested action
3. **ASK** user how to proceed:
   - Retry?
   - Use different agent?
   - Cancel task?

**DO NOT:**
- Continue to next step silently
- Hide or minimize errors
- Assume errors will resolve themselves

---

## Reporting to User

After dispatching, **IMMEDIATELY** report to the user in this structured format:

**Required Information:**

1. **Dispatch Status**
   - Task ID (for follow-up)
   - Agent selected (which agent is running)
   - Dispatch result (success/failure)

2. **Monitoring Details**
   - Cron job created (yes/no)
   - Job ID (for manual cleanup)
   - Monitoring frequency (e.g., "every 5 minutes")
   - Next check time (estimated)
   - Auto-delete enabled (yes/no)

3. **Agent Environment**
   - Worktree path
   - Branch name (e.g., `agent/<task-id>`)
   - Tmux session name

4. **Follow-up Commands**
   - How to check progress manually
   - How to attach to tmux session
   - How to view monitoring job status

**Example Report:**

```
✅ Task Dispatched Successfully

📋 Task Details:
- Task ID: feat-auth
- Agent: OpenCode (claude-sonnet-4.6)
- Status: Running

🔍 Monitoring:
- Cron Job: ✅ Created
- Job ID: d037ed80-56eb-43be-a8c0-e95132b9e426
- Frequency: Every 5 minutes
- Next Check: ~5 minutes
- Auto-delete: ✅ Enabled (when task completes)

📁 Environment:
- Worktree: /home/admin/openclaw/workspace/../agent-worktrees/feat-auth
- Branch: agent/feat-auth
- Tmux: agent-feat-auth

🛠️ Manual Commands:
- Check progress: tmux attach -t agent-feat-auth
- View monitoring: cron.list()
- View worktree: cd ../agent-worktrees/feat-auth
```

**Important:**
- Report IMMEDIATELY after dispatch (don't wait for first monitoring cycle)
- Include ALL details in first report
- **MANDATORY**: If dispatch fails, report error immediately with full details
- **MANDATORY**: If monitoring creation fails, report it immediately (don't continue silently)
- **MANDATORY**: If ANY step fails, STOP and report to user before proceeding
- Use ❌ emoji for errors to make them visible
- Always include the exact error message from tools/scripts
- Suggest concrete actions user can take to resolve the issue

---

## Checklist Before Dispatching

- [ ] Task is complex enough (simple queries should not spawn agents)
- [ ] Agent is selected correctly (consult dispatch table in `TOOLS.md`)
- [ ] Prompt is clear and specific (vague prompts waste agent time)
- [ ] Monitoring cron job is created (otherwise you'll lose track)

---

*Last updated: 2026-03-12*
