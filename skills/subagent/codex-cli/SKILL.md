---
name: codex-cli
description: Execute Codex CLI in a one-shot wrapper for project-scoped code analysis, refactoring, and automated code changes. Use when you need a non-interactive Codex command instead of the tmux/TUI launcher.
---

# Codex CLI integration

## Overview

Execute Codex CLI commands and parse structured JSON responses. Supports file references via `@` syntax, multiple models, and sandbox controls.

## When to Use

- Complex code analysis requiring deep understanding
- Large-scale refactoring across multiple files
- Automated code generation with safety controls
- Tasks requiring specialized reasoning models (o3, gpt-5)

## Usage

**Recommended:** use `uv run` to manage the Python environment automatically.
```bash
uv run ./scripts/codex.py "<task>" [model] [working_dir]
```

**Alternatives:** run the script directly or invoke it with Python.
```bash
./scripts/codex.py "<task>" [model] [working_dir]
# or
python3 ./scripts/codex.py "<task>" [model] [working_dir]
```

Resume a session:
```bash
uv run ./scripts/codex.py resume <session_id> "<task>" [model] [working_dir]
```

## Timeout Control

- **Built-in**: Script enforces 2-hour timeout by default
- **Override**: Set `CODEX_TIMEOUT` environment variable (in milliseconds, e.g., `CODEX_TIMEOUT=3600000` for 1 hour)
- **Behavior**: On timeout, sends SIGTERM, then SIGKILL after 5s if process doesn't exit
- **Exit code**: Returns 124 on timeout (consistent with GNU timeout)
- **Bash tool**: Always set `timeout: 7200000` parameter for double protection

### Parameters

- `task` (required): Task description, supports `@file` references
- `model` (optional): Model to use (default: gpt-5.2-codex)
  - `gpt-5.4`: Default, optimized for code
  - `gpt-5-codex`: Previous version
  - `gpt-5`: Fast general purpose
- `working_dir` (optional): Working directory (default: current)

### Return Format

Extracts `agent_message` from Codex JSON stream and appends session ID:
```
Agent response text here...

---
SESSION_ID: 019a7247-ac9d-71f3-89e2-a823dbd8fd14
```

Error format (stderr):
```
ERROR: Error message
```

### Output Saving

After each run, the wrapper saves output to `.tmp/docs/output/`:
- **Filename**: `out_<date>_<time>_codex_<task>.md`
- **Content**: timestamp, task text, optional session ID, and the full final output

On success, stderr includes a message such as:
```
INFO: Output saved to .tmp/docs/output/out_20240125_143052_codex_task.md
```

### Invocation Pattern

When calling via Bash tool, always include the timeout parameter:
```
Bash tool parameters:
- command: uv run ./scripts/codex.py "<task>" [model] [working_dir]
- timeout: 7200000
- description: <brief description of the task>
```

Alternatives:
```
# Direct execution (simplest)
- command: ./scripts/codex.py "<task>" [model] [working_dir]

# Using python3
- command: python3 ./scripts/codex.py "<task>" [model] [working_dir]
```

### Examples

**Basic code analysis:**
```bash
# Recommended: via uv run (auto-manages Python environment)
uv run ./scripts/codex.py "explain @src/main.ts"
# timeout: 7200000

# Alternative: direct execution
./scripts/codex.py "explain @src/main.ts"
```

**Refactoring with specific model:**
```bash
uv run ./scripts/codex.py "refactor @src/utils for performance" "gpt-5"
# timeout: 7200000
```

**Multi-file analysis:**
```bash
uv run ./scripts/codex.py "analyze @. and find security issues" "gpt-5-codex" "/path/to/project"
# timeout: 7200000
```

**Resume previous session:**
```bash
# First session
uv run ./scripts/codex.py "add comments to @utils.js" "gpt-5-codex"
# Output includes: SESSION_ID: 019a7247-ac9d-71f3-89e2-a823dbd8fd14

# Continue the conversation
uv run ./scripts/codex.py resume 019a7247-ac9d-71f3-89e2-a823dbd8fd14 "now add type hints"
# timeout: 7200000
```

## Notes

- **Recommended**: Use `uv run` for automatic Python environment management (requires uv installed)
- **Alternative**: Direct execution `./scripts/codex.py` (uses system Python via shebang)
- Python implementation using standard library (zero dependencies)
- Cross-platform compatible (Windows/macOS/Linux)
- PEP 723 compliant (inline script metadata)
- Runs with `--dangerously-bypass-approvals-and-sandbox` for automation (new sessions only)
- Uses `--skip-git-repo-check` to work in any directory
- Streams progress, returns only final agent message
- Every execution returns a session ID for resuming conversations
- Requires Codex CLI installed and authenticated
