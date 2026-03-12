# Easy Skills

🚀 A curated collection of high-quality AI agent skills for enhanced productivity and automation.

## Overview

Easy Skills provides a set of powerful, ready-to-use agent skills designed to streamline your workflow. Each skill is carefully crafted to handle specific tasks efficiently, from code analysis to academic writing assistance.

## Skills

### 🤖 Subagent Skills

AI-powered subagent integrations with automatic fallback support.

#### [Agent Dispatch](./skills/subagent/agent-dispatch/SKILL.md)
Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated worktrees, branches, and tmux sessions with automatic monitoring and failure recovery.

**Features:**
- Isolated worktree + branch + tmux session creation
- Automatic monitoring via cron jobs
- Failure recovery via Ralph Loop
- Cross-platform compatibility

#### [OpenCode](./skills/subagent/opencode/SKILL.md)
Execute OpenCode CLI for AI-powered code analysis, refactoring, and automated code changes.

**Features:**
- Multi-model support (Claude, GPT, Gemini)
- Session resumption support
- File reference via `@` syntax
- Cross-platform compatibility

#### [Gemini](./skills/subagent/gemini/SKILL.md)
Execute Gemini CLI for AI-powered code analysis and generation.

**Features:**
- Support for multiple Gemini models
- Cross-platform compatibility
- Output saving and session management
- No fallback - pure Gemini CLI execution

#### [Codex](./skills/subagent/codex/SKILL.md)
Execute Codex CLI for code analysis, refactoring, and automated code changes.

**Features:**
- Session resumption support
- File reference via `@` syntax
- Structured JSON output parsing
- Default model: gpt-5.4

### 🚀 Efficiency Skills

Productivity-enhancing agent behaviors.

#### [PUA](./skills/efficiency/pua/skills/pua/SKILL.md) | [English Version](./skills/efficiency/pua/skills/pua-en/SKILL.md)
Forces exhaustive problem-solving using corporate PUA rhetoric and structured debugging methodology.

**Features:**
- Auto-triggers on repeated failures or user frustration
- Prevents passive "I cannot" responses
- Enforces exhaustive debugging before giving up
- Applies to all task types: code, config, research, deployment

## Installation

Skills are designed to be used with the [OpenCode](https://github.com/OhMyOpenCode/opencode) framework. Simply clone this repository and reference the skills in your OpenCode configuration.

```bash
git clone https://github.com/your-username/easy-skills.git
```

## Usage

Each skill includes a detailed `SKILL.md` file with usage instructions, examples, and configuration options. Navigate to the skill directory to learn more.

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

Made with ❤️ by the Easy Skills team
