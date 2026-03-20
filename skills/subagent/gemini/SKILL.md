---
name: gemini
description: Execute Gemini CLI in a one-shot wrapper for project-scoped code analysis and generation. Use when you need a non-interactive Gemini command instead of the tmux/TUI launcher.
---

# Gemini CLI integration

## Overview

Execute Gemini CLI commands with support for multiple models and flexible prompt input. Integrates Google's Gemini AI models into Claude Code workflows.

## When to Use

- Complex reasoning tasks requiring advanced AI capabilities
- Code generation and analysis with Gemini models
- Tasks requiring Google's latest AI technology
- Alternative perspective on code problems

## Usage

**Recommended:** use `uv run` to manage the Python environment automatically.
```bash
uv run ./scripts/gemini.py "<prompt>" [working_dir]
```

**Alternatives:** run the script directly or invoke it with Python.
```bash
./scripts/gemini.py "<prompt>" [working_dir]
# or
python3 ./scripts/gemini.py "<prompt>" [working_dir]
```

## Environment Variables

- **GEMINI_MODEL**: Configure model (default: `gemini-3-pro-preview`)
  - Example: `export GEMINI_MODEL=gemini-3`

## Timeout Control

- **Fixed**: 7200000 milliseconds (2 hours), immutable
- **Bash tool**: Always set `timeout: 7200000` for double protection

### Parameters

- `prompt` (required): Task prompt or question
- `working_dir` (optional): Working directory (default: current directory)

### Return Format

Plain text output from Gemini:

```text
Model response text here...
```

Error format (stderr):

```text
ERROR: Error message
```

### Output Saving

After each run, the wrapper saves output to `.tmp/docs/output/`:
- **Filename**: `out_<date>_<time>_gemini_<task>.md`
- **Content**: timestamp, model, prompt, and the full Gemini output

On success, stderr includes a message such as:
```
INFO: Output saved to .tmp/docs/output/out_20240125_150321_gemini_task.md
```

### Invocation Pattern

When calling via Bash tool, always include the timeout parameter:

```yaml
Bash tool parameters:
- command: uv run ./scripts/gemini.py "<prompt>"
- timeout: 7200000
- description: <brief description of the task>
```

Alternatives:

```yaml
# Direct execution (simplest)
- command: ./scripts/gemini.py "<prompt>"

# Using python3
- command: python3 ./scripts/gemini.py "<prompt>"
```

### Examples

**Basic query:**

```bash
uv run ./scripts/gemini.py "explain quantum computing"
# timeout: 7200000
```

**Code analysis:**

```bash
uv run ./scripts/gemini.py "review this code for security issues: $(cat app.py)"
# timeout: 7200000
```

**With specific working directory:**

```bash
uv run ./scripts/gemini.py "analyze project structure" "/path/to/project"
# timeout: 7200000
```

## Scripts Reference

| Script | Purpose |
|------|---------|
| `scripts/gemini.py` | Main wrapper script that executes Gemini CLI |

## Notes

- **Recommended**: Use `uv run` for automatic Python environment management (requires uv installed)
- **Alternative**: Direct execution `./scripts/gemini.py` (uses system Python via shebang)
- Python implementation using standard library (zero dependencies)
- Cross-platform compatible (Windows/macOS/Linux)
- PEP 723 compliant (inline script metadata)
- Requires Gemini CLI installed and authenticated
- Supports all Gemini model variants (configure via `GEMINI_MODEL` environment variable)
- Output is streamed directly from Gemini CLI
