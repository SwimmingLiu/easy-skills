---
name: codex
description: Launch Codex as a subagent skill in interactive TUI mode. Use when a task should be handed to Codex for ongoing work in a live session instead of a one-shot wrapper. Default launch mode is permissive and interactive: `codex --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox`.
---

# Codex

Use this skill when you want Codex itself to be the execution subagent.

## Purpose

This is an execution-agent skill.

It tells the caller how to launch Codex as a live subagent session, especially
in tmux-backed dispatch flows.

## Default launch

Launch Codex in interactive TUI mode with permissive defaults:

```bash
codex --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox
```

## Use this skill for

- live multi-turn code work,
- debugging and refactoring sessions,
- implementation sessions that should stay open,
- agent-dispatch flows that choose Codex as the execution agent.

## Not this skill

If the caller wants deterministic one-shot execution, use a separate
`codex-cli` style skill instead of this one.
