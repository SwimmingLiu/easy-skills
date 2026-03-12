---
name: opencode
description: Execute OpenCode CLI for code analysis, refactoring, and automated code changes. Use when you need to delegate complex code tasks to OpenCode AI with file references (@syntax), multi-model support, and session management. Supports multiple providers (GitHub Copilot, Google, OpenAI, Zhipu) and models.
---

# OpenCode CLI Integration

## Overview

Execute OpenCode CLI commands for AI-powered code tasks. Supports file references via `@` syntax, multiple models and providers, session management, and structured output.

## When to Use

- Complex code analysis requiring deep understanding
- Large-scale refactoring across multiple files
- Automated code generation with safety controls
- Tasks requiring specialized reasoning models
- Multi-model workflows with provider selection

## Usage

**推荐方式**（使用 uv run，自动管理 Python 环境）：
```bash
uv run ./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]
```

**备选方式**（直接执行或使用 Python）：
```bash
./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]
# 或
python3 ./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]
```

恢复会话:
```bash
uv run ./.claude/skills/opencode/scripts/opencode.py resume <session_id> "<task>" [model] [working_dir]
```

## Environment Variables

- **OPENCODE_MODEL**: Override model (default: uses CLI default model)
- **OPENCODE_AGENT**: Configure agent (default: none, uses default agent)

## Timeout Control

- **Fixed**: 7200000 milliseconds (2 hours), immutable
- **Bash tool**: Always set `timeout: 7200000` for double protection

### Parameters

- `task` (required): Task description, supports `@file` references
- `model` (optional): Model to use (default: uses CLI default)
  - `claude-sonnet-4.6`: Balanced performance
  - `claude-opus-4.6`: High-performance reasoning
  - `gpt-5.4`: Code-optimized
  - `gemini-3-pro-preview`: Google's latest
  - See `opencode models` for full list
- `working_dir` (optional): Working directory (default: current)

### Return Format

Plain text output from OpenCode with session ID:
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

每次执行后，输出结果会自动保存到 `.tmp/docs/output/` 目录：
- **文件名**: `out_<日期>_<时间>_opencode_<任务描述>.md`
- **内容包含**: 生成时间、Model、Session ID（如适用）、Prompt、完整输出

保存成功后会在 stderr 输出提示：
```
INFO: Output saved to .tmp/docs/output/out_20240125_143052_opencode_task.md
```

### Invocation Pattern

When calling via Bash tool, always include the timeout parameter:
```
Bash tool parameters:
- command: uv run ./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]
- timeout: 7200000
- description: <brief description of the task>
```

Alternatives:
```
# Direct execution (simplest)
- command: ./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]

# Using python3
- command: python3 ./.claude/skills/opencode/scripts/opencode.py "<task>" [model] [working_dir]
```

### Examples

**Basic code analysis:**
```bash
# Recommended: via uv run (auto-manages Python environment)
uv run ./.claude/skills/opencode/scripts/opencode.py "explain @src/main.ts"
# timeout: 7200000

# Alternative: direct execution
./.claude/skills/opencode/scripts/opencode.py "explain @src/main.ts"
```

**With specific model:**
```bash
uv run ./.claude/skills/opencode/scripts/opencode.py "refactor @src/utils for performance" "claude-opus-4.6"
# timeout: 7200000
```

**Multi-file analysis:**
```bash
uv run ./.claude/skills/opencode/scripts/opencode.py "analyze @. and find security issues" "gpt-5.2-codex" "/path/to/project"
# timeout: 7200000
```

**Resume previous session:**
```bash
# First session
uv run ./.claude/skills/opencode/scripts/opencode.py "add comments to @utils.js"
# Output includes: SESSION_ID: 019a7247-ac9d-71f3-89e2-a823dbd8fd14

# Continue the conversation
uv run ./.claude/skills/opencode/scripts/opencode.py resume 019a7247-ac9d-71f3-89e2-a823dbd8fd14 "now add type hints"
# timeout: 7200000
```

**With specific agent:**
```bash
# Set agent via environment variable
OPENCODE_AGENT=paper uv run ./.claude/skills/opencode/scripts/opencode.py "your task"
```

## Available Models

Run `opencode models` to see all available models. Popular choices:

| Provider | Model | Use Case |
|----------|-------|----------|
| **github-copilot** | `claude-sonnet-4.6` | Default, balanced |
| **github-copilot** | `claude-opus-4.6` | Complex reasoning |
| **github-copilot** | `gpt-5.2-codex` | Code optimization |
| **google** | `gemini-3-pro-preview` | Google's latest |
| **zhipuai** | `glm-5` | Chinese tasks |

## Notes

- **Recommended**: Use `uv run` for automatic Python environment management (requires uv installed)
- **Alternative**: Direct execution `./opencode.py` (uses system Python via shebang)
- Python implementation using standard library (zero dependencies)
- Cross-platform compatible (Windows/macOS/Linux)
- PEP 723 compliant (inline script metadata)
- Requires OpenCode CLI installed (`npm install -g opencode`)
- Streams output in real-time
- Every execution returns a session ID for resuming conversations
