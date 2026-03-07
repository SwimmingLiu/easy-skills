---
name: gemini
description: Execute Gemini CLI for AI-powered code analysis and generation with automatic fallback. Use when you need to leverage Google's Gemini models for complex reasoning tasks. Automatically falls back to OpenCode paper agent with Tuzi API gemini-3-pro when Gemini CLI is unavailable (rate limits, quota exceeded, authentication issues).
---

# Gemini CLI Integration

## Overview

Execute Gemini CLI commands with support for multiple models and flexible prompt input. Integrates Google's Gemini AI models into Claude Code workflows. **支持自动降级**：当 Gemini CLI 不可用时，自动切换到 OpenCode paper agent 模式。

## When to Use

- Complex reasoning tasks requiring advanced AI capabilities
- Code generation and analysis with Gemini models
- Tasks requiring Google's latest AI technology
- Alternative perspective on code problems

## Automatic Fallback (自动降级)

脚本内置自动降级机制，无需手动干预。

### 触发降级的场景

以下错误会自动触发降级：
- `rate limit exceeded` - 速率限制
- `quota exceeded` / `insufficient quota` - 额度用尽
- `authentication failed` / `401` / `403` - 认证失败
- `account suspended` / `account restricted` - 账户受限
- `billing` / `payment` 相关错误 - 计费问题
- `api key invalid` / `api key expired` - API Key 问题
- `connection timeout` / `network error` - 网络问题
- `service unavailable` / `503` / `429` - 服务不可用
- `gemini command not found` - CLI 未安装

### 降级方案

**自动降级到 OpenCode `paper` Agent 模式**：
- **Agent**: `paper`
- **Model**: `tuzi/gemini-3-flash-preview-all`
- **调用方式**: `opencode run --agent paper --model "tuzi/gemini-3-flash-preview-all" "<prompt>"`

降级时会在 stderr 输出警告：
```
WARN: Gemini CLI unavailable, falling back to OpenCode paper agent
INFO: Using agent=paper, model=tuzi/gemini-3-pro
```

### 手动降级

如需直接使用降级方案，可调用独立的降级脚本：

```bash
# 直接调用降级脚本（推荐）
uv run ./.claude/skills/gemini/scripts/gemini_fallback.py "<prompt>" [working_dir]

# 或直接使用 OpenCode CLI
opencode run --agent paper --model "tuzi/gemini-3-flash-preview-all" "<prompt>"

# 如果出现 Session not found
OPENCODE_SERVER_PASSWORD= opencode run --agent paper --model "tuzi/gemini-3-flash-preview-all" "<prompt>"
```

## Usage

**推荐方式**（使用 uv run，自动管理 Python 环境）：
```bash
uv run ./.claude/skills/gemini/scripts/gemini.py "<prompt>" [working_dir]
```

**备选方式**（直接执行或使用 Python）：
```bash
./.claude/skills/gemini/scripts/gemini.py "<prompt>" [working_dir]
# 或
python3 ./.claude/skills/gemini/scripts/gemini.py "<prompt>" [working_dir]
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

Plain text output from Gemini (or fallback):

```text
Model response text here...
```

Error format (stderr):

```text
ERROR: Error message
```

Fallback warning (stderr):
```text
WARN: Gemini CLI unavailable, falling back to OpenCode paper agent
```

### Output Saving

每次执行后，输出结果会自动保存到 `.tmp/docs/output/` 目录：
- **正常模式文件名**: `out_<日期>_<时间>_gemini_<任务描述>.md`
- **降级模式文件名**: `out_<日期>_<时间>_gemini_fallback_<任务描述>.md`
- **内容包含**: 生成时间、Agent 类型、Model、Prompt、完整输出

保存成功后会在 stderr 输出提示：
```
INFO: Output saved to .tmp/docs/output/out_20240125_150321_gemini_task.md
```

### Invocation Pattern

When calling via Bash tool, always include the timeout parameter:

```yaml
Bash tool parameters:
- command: uv run ./.claude/skills/gemini/scripts/gemini.py "<prompt>"
- timeout: 7200000
- description: <brief description of the task>
```

Alternatives:

```yaml
# Direct execution (simplest)
- command: ./.claude/skills/gemini/scripts/gemini.py "<prompt>"

# Using python3
- command: python3 ./.claude/skills/gemini/scripts/gemini.py "<prompt>"

# Direct fallback (skip Gemini CLI attempt)
- command: uv run ./.claude/skills/gemini/scripts/gemini_fallback.py "<prompt>"
```

### Examples

**Basic query:**

```bash
uv run ./.claude/skills/gemini/scripts/gemini.py "explain quantum computing"
# timeout: 7200000
```

**Code analysis:**

```bash
uv run ./.claude/skills/gemini/scripts/gemini.py "review this code for security issues: $(cat app.py)"
# timeout: 7200000
```

**With specific working directory:**

```bash
uv run ./.claude/skills/gemini/scripts/gemini.py "analyze project structure" "/path/to/project"
# timeout: 7200000
```

**Direct fallback usage:**

```bash
# Skip Gemini CLI, directly use OpenCode paper agent
uv run ./.claude/skills/gemini/scripts/gemini_fallback.py "your prompt here"
```

## Scripts Reference

| 脚本 | 用途 |
|------|------|
| `scripts/gemini.py` | 主脚本，支持自动降级 |
| `scripts/gemini_fallback.py` | 独立降级脚本，直接使用 OpenCode paper agent |

## Notes

- **Recommended**: Use `uv run` for automatic Python environment management (requires uv installed)
- **Alternative**: Direct execution `./gemini.py` (uses system Python via shebang)
- Python implementation using standard library (zero dependencies)
- Cross-platform compatible (Windows/macOS/Linux)
- PEP 723 compliant (inline script metadata)
- Requires Gemini CLI installed and authenticated (for primary mode)
- Supports all Gemini model variants (configure via `GEMINI_MODEL` environment variable)
- Output is streamed directly from Gemini CLI or OpenCode
- **Automatic fallback**: No manual intervention needed when Gemini CLI fails

## Fallback Quick Reference

| 场景 | 降级方案 |
|------|----------|
| Gemini CLI 失败 | OpenCode `paper` agent + `tuzi/gemini-3-pro` 模型 |
| Gemini CLI 未安装 | OpenCode `paper` agent + `tuzi/gemini-3-pro` 模型 |

**快速降级命令**：
```bash
# 自动降级（推荐）
uv run ./.claude/skills/gemini/scripts/gemini.py "<your prompt>"

# 手动降级
uv run ./.claude/skills/gemini/scripts/gemini_fallback.py "<your prompt>"

# 或直接使用 OpenCode
opencode run --agent paper --model "tuzi/gemini-3-pro" "<your prompt>"
```
