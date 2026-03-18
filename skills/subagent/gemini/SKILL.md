---
name: gemini
description: Launch Gemini as a subagent skill in interactive TUI mode. Use when a task should be handed to Gemini for ongoing work in a live session instead of a one-shot wrapper. Default launch mode is permissive and interactive: `gemini --yolo`.
---

# Gemini

Use this skill when you want Gemini itself to be the execution subagent.

## Purpose

This is an execution-agent skill.

It tells the caller how to launch Gemini as a live subagent session, especially
in tmux-backed dispatch flows.

## Default launch

Launch Gemini in interactive TUI mode with permissive defaults:

```bash
gemini --yolo
```

## Use this skill for

- live multi-turn work,
- ongoing reasoning sessions,
- writing and analysis sessions that should stay open,
- agent-dispatch flows that choose Gemini as the execution agent.

## Not this skill

If the caller wants deterministic one-shot execution, use a separate
`gemini-cli` style skill instead of this one.
