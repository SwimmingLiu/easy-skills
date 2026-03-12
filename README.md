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

#### [PUA](./skills/efficiency/pua/SKILL.md) | [English Version](./skills/efficiency/pua-en/SKILL.md)
Forces exhaustive problem-solving using corporate PUA rhetoric and structured debugging methodology.

**Features:**
- Auto-triggers on repeated failures or user frustration
- Prevents passive "I cannot" responses
- Enforces exhaustive debugging before giving up
- Applies to all task types: code, config, research, deployment

### 🎨 Frontend Skills

Frontend design and development skills from the [impeccable](https://github.com/pbakaus/impeccable) collection.

#### [Frontend Design](./skills/frontend/frontend-design/SKILL.md)
Create distinctive, production-grade frontend interfaces with high design quality.

**Features:**
- Generates creative, polished code
- Avoids generic AI aesthetics
- Includes reference docs for color, typography, motion, and UX design
- Perfect for building web components, pages, and applications

**Additional Frontend Skills:**
- **animate** - Add smooth, purposeful animations
- **audit** - Review and improve code quality
- **clarify** - Improve code clarity and readability
- **colorize** - Add color and visual appeal
- **critique** - Provide constructive feedback
- **delight** - Add delightful micro-interactions
- **distill** - Simplify complex code
- **extract** - Extract reusable components
- **harden** - Improve code robustness
- **normalize** - Standardize code patterns
- **optimize** - Improve performance
- **polish** - Refine and perfect details
- **quieter** - Reduce visual noise

## Installation

### For Agents (Automatic Installation)

Agents can install skills directly from this repository using the `skills` CLI:

```bash
# Install a specific skill globally
npx skills add https://github.com/SwimmingLiu/easy-skills@<skill-path> -g -y

# Examples:
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/subagent/opencode -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/efficiency/pua -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/efficiency/pua-en -g -y
```

### For Humans (Manual Installation)

1. Clone this repository:
```bash
git clone https://github.com/SwimmingLiu/easy-skills.git
cd easy-skills
```

2. Install a skill to your agent:
```bash
# From local path
npx skills add ./skills/subagent/opencode -g -y

# Or copy the skill directory to your agent's skills folder
cp -r skills/subagent/opencode ~/.agents/skills/
```

### Verify Installation

After installation, verify the skill is available:
```bash
npx skills list
```

The skill should appear in the list and will be automatically loaded by your agent.

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
