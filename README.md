# Easy Skills

🚀 A curated collection of high-quality AI agent skills for enhanced productivity and automation.

## Overview

Easy Skills provides a set of powerful, ready-to-use agent skills designed to streamline your workflow. Each skill is carefully crafted to handle specific tasks efficiently, from code analysis to academic writing assistance.

## Skills

### 🤖 Subagent Skills

AI-powered subagent integrations with automatic fallback support.

#### [Agent Dispatch](./skills/agent-dispatch/SKILL.md)
Dispatch tasks to execution agents (OpenCode, Gemini, Codex) via isolated worktrees, branches, and tmux sessions with automatic monitoring and failure recovery.

**Features:**
- Cross-repo worktree dispatch with explicit `REPO_ROOT` support
- Automatic target repo detection from the current git repository
- Prompt handoff via prompt file + runner script to avoid shell parsing bugs
- Safe handling for multi-line prompts, fenced code blocks, quotes, and backticks
- Isolated worktree + branch + tmux session creation
- Automatic monitoring via cron jobs
- Failure recovery guidance for failed runs

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

### 📊 Diagram Skills

Diagram creation and validation tools.

#### [Draw.io](./skills/diagram/drawio/SKILL.md)
Generate draw.io diagrams as native `.drawio` files with optional export to PNG/SVG/PDF.

**Features:**
- Native .drawio file generation
- Export to PNG, SVG, or PDF with embedded XML
- Diagrams remain editable after export

#### [Mermaid Diagrams](./skills/diagram/mermaid-diagrams/SKILL.md)
Comprehensive guide for creating software diagrams using Mermaid syntax.

**Features:**
- Class diagrams, sequence diagrams, flowcharts, ERDs
- C4 architecture diagrams, state diagrams, git graphs
- Text-based, version-controllable diagrams

#### [Mermaid Correction](./skills/diagram/mermaid-correction/SKILL.md)
Validate, diagnose, and repair Mermaid code blocks with iterative check → correct → re-check workflow.

**Features:**
- Automatic syntax validation via Mermaid CLI
- Detailed parse error reporting with line/column info
- Up to 3 correction attempts with re-validation

### 🌐 Language Skills

Translation and localization tools.

#### [Baoyu Translate](./skills/language/baoyu-translate/SKILL.md)
Multi-mode translation skill with quick, normal, and refined workflows.

**Features:**
- Three modes: quick (direct), normal (analyze then translate), refined (full review)
- Custom glossaries and terminology consistency
- Supports document and article translation

### 📝 Markdown Skills

Markdown processing and conversion tools.

#### [Baoyu Format Markdown](./skills/markdown/baoyu-format-markdown/SKILL.md)
Format plain text or markdown with frontmatter, titles, summaries, and proper structure.

**Features:**
- Adds frontmatter, headings, bold, lists, code blocks
- Preserves original content, only adjusts formatting
- Outputs to {filename}-formatted.md

#### [Baoyu Markdown to HTML](./skills/markdown/baoyu-markdown-to-html/SKILL.md)
Convert Markdown to styled HTML with WeChat-compatible themes.

**Features:**
- Code highlighting, math, PlantUML support
- Footnotes, alerts, infographics
- Optional bottom citations for external links

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

For `agent-dispatch`, prefer these usage patterns:

```bash
# Dispatch against the current git repo
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh \
  fix-login codex "Fix the login redirect bug in src/auth/login.ts"

# Dispatch against another project explicitly
REPO_ROOT=/home/admin/projects/ClassPets \
/home/admin/openclaw/workspace/scripts/agent-orchestration/spawn-agent.sh \
  feat-auth opencode "Implement JWT authentication in src/api/auth.ts"
```

`agent-dispatch` now writes prompts to a prompt file and lets the runner script
read them inside tmux. This avoids quoting bugs where multi-line prompts or
TypeScript code blocks could be misread as shell input.

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

Made with ❤️ by the Easy Skills team
