---
name: agent-dispatch
description: Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated
  worktrees, branches, and tmux sessions. Use when OpenClaw needs to spawn an agent
  for any code change, documentation writing, bug fixing, code review, or git
  operation. Handles the full lifecycle: environment creation, agent startup,
  task registration, monitoring, and failure recovery via Ralph Loop.
---

# Agent dispatch

This skill encapsulates the full workflow for dispatching tasks to execution
agents. OpenClaw calls this skill whenever it needs to start an agent.

## Dispatch command

Run `spawn-agent.sh` from the workspace root to create an isolated environment
and start the agent:

```bash
./scripts/agent-orchestration/spawn-agent.sh <task-id> <agent> "<prompt>" [model]
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
./scripts/agent-orchestration/spawn-agent.sh feat-auth opencode \
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

## Reporting to the user

After running `spawn-agent.sh`, always tell the user:

- **Task ID** — so they can follow up.
- **Agent selected** — so they know what's running.
- **How to watch** — `tmux attach -t agent-<task-id>`.
- **How to check status** — `./scripts/agent-orchestration/check-agents.sh`.

## Monitoring

`check-agents.sh` runs automatically every 10 minutes via cron. It checks:

- Whether the tmux session is still alive.
- Whether a PR has been created for the branch.
- Whether CI checks have passed.

It notifies you when a PR is ready or when an agent has failed.

To check manually:

```bash
./scripts/agent-orchestration/check-agents.sh
```

To attach to a running session:

```bash
tmux attach -t agent-<task-id>
```

## Failure recovery (Ralph Loop)

When an agent session ends without a PR, `check-agents.sh` triggers
`ralph-loop.sh`, which analyzes the failure and restarts the agent with
added context. It retries up to three times before notifying you of a
permanent failure.

## Directory layout

```
workspace/
├── .clawdbot/
│   ├── active-tasks.json          # live task registry
│   └── prompts/                   # Ralph Loop recovery prompts
├── scripts/agent-orchestration/
│   ├── spawn-agent.sh             # create environment and start agent
│   ├── check-agents.sh            # monitor all active agents
│   ├── ralph-loop.sh              # automatic failure recovery
│   ├── notify.sh                  # send desktop/system notification
│   └── cleanup.sh                 # remove completed worktrees
└── ../agent-worktrees/            # agent working directories (one per task)
```
