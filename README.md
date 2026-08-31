# Easy Skills

🚀 A curated collection of high-quality AI agent skills for enhanced productivity and automation.

## Overview

Easy Skills provides a set of powerful, ready-to-use agent skills designed to streamline your workflow. Each skill is carefully crafted to handle specific tasks efficiently, from code analysis to academic writing assistance.

## Skills

### Meta Skills

Skills for building and governing other Agent Skills.

#### [Skill Lifecycle](./skills/meta/skill-lifecycle/SKILL.md)

Discover, create, review, evaluate, optimize, and maintain Agent Skills through explicit evidence, quality gates, versioned state, and rollback-safe decisions.

```bash
# Install from this checkout
npx skills add ./skills/meta/skill-lifecycle -g -y

# Install from GitHub
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/meta/skill-lifecycle -g -y
```

### 🤖 Subagent Skills

AI-powered subagent integrations with automatic fallback support.

#### [Agent Dispatch](./skills/subagent/agent-dispatch/SKILL.md)
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
Launch the OpenCode terminal UI inside a dedicated tmux session for interactive project work.

**Features:**
- Detached tmux session creation
- Prompt handoff through tmux buffer staging
- Machine-readable session metadata
- Explicit exit codes for setup failures

#### [Gemini](./skills/subagent/gemini/SKILL.md)
Launch the Gemini terminal UI inside a dedicated tmux session for interactive project work.

**Features:**
- Detached tmux session creation
- Prompt handoff through tmux buffer staging
- Machine-readable session metadata
- Explicit exit codes for setup failures

#### [Codex](./skills/subagent/codex/SKILL.md)
Launch the Codex terminal UI inside a dedicated tmux session for interactive project work.

**Features:**
- Detached tmux session creation
- Prompt handoff through tmux buffer staging
- Machine-readable session metadata
- Explicit exit codes for setup failures

#### [GLM Eyes](./skills/subagent/glm-eyes/SKILL.md)
Vision fallback for text-only main models (e.g. GLM-5.2). Spawns a sub-agent that calls any multimodal Claude-compatible provider to read an image and return a text description.

**Features:**
- Model-agnostic: auto-discovers any vision-capable provider in your CC-Switch routes (Kimi, Claude, GPT-4o, Qwen-VL, GLM-4V, Gemini, …); add a provider in CC-Switch and it just works
- Reads credentials live from the CC-Switch database — no hardcoded API keys
- Automatic failover across available multimodal providers (no dead end on a single 503)
- Refuses to call non-vision models to avoid wasting a request
- Zero third-party dependencies (Python standard library only)

### 🖼️ Image Skills

Image-generation integrations and fallback workflows.

#### [Image Gen Rightcodes](./skills/image/image-gen-rightcodes/SKILL.md)
Use RightAPI's asynchronous image-generation protocol as an explicit CLI fallback for image generation and editing.

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

### 🔬 Scientific Writing Skills

- [Check AI Write](./skills/scientific/check-ai-write/SKILL.md) - Detect and reduce common AI-writing patterns.
- [Correct Wrong Words](./skills/scientific/correct-wrong-words/SKILL.md) - Check and correct Chinese and English typos while protecting technical terms.
- [Paper Rewrite](./skills/scientific/paper-rewrite/SKILL.md) - Rewrite and polish academic papers.

### 🧠 Knowledge Skills

#### [Knowledge Base](./skills/knowledge/knowledge-base/SKILL.md)
Operate a Codex-native Markdown and Obsidian personal knowledge base with durable sources and traceable synthesis.

**Features:**
- Deterministic, idempotent source ingestion
- Connected Wiki notes with explicit source links
- Local retrieval with provenance and health checks
- Codex Agent Skill metadata and standard-library Python tooling

#### Additional Knowledge Skills

- [Image OCR](./skills/knowledge/image-ocr/SKILL.md) - Extract text from images, screenshots, scans, and image-based PDFs.
- [LLM Wiki Init](./skills/knowledge/llm-wiki-init/SKILL.md) - Initialize a maintainable local LLM Wiki structure.
- [Local Audio Transcriber](./skills/knowledge/local-audio-transcriber/SKILL.md) - Transcribe local audio or video into text, subtitles, or Markdown notes.
- [Subtitle Proofreader](./skills/knowledge/subtitle-proofreader/SKILL.md) - Proofread subtitles and transcripts, including speech-recognition errors and terminology.
- [Video Downloader](./skills/knowledge/video-downloader/SKILL.md) - Download videos and optional subtitles from supported platforms.

### External Skill Repositories

These skills are tracked as Git submodules. Their source remains in the original repositories, so the project stores only submodule pointers and configuration.

#### [StoryWeave](https://github.com/SwimmingLiu/StoryWeave)

StoryWeave provides three independent skills for 16:9 presentations:

- [StoryWeave HTML](./skills/storyweave/skills/storyweave-html/SKILL.md) - Create editable standalone HTML slides.
- [StoryWeave Imagegen](./skills/storyweave/skills/storyweave-imagegen/SKILL.md) - Create image-based presentation pages and exports.
- [StoryWeave Express](./skills/storyweave/skills/storyweave-express/SKILL.md) - Package existing HTML or image pages for Bento.

#### [Voiceforge](https://github.com/SwimmingLiu/Voiceforge)

- [Voiceforge](./skills/voiceforge/SKILL.md) - Draft, rewrite, polish, and edit Chinese or English reader-facing content.

## Installation

### For Agents (Automatic Installation)

Agents can install skills directly from this repository using the `skills` CLI:

```bash
# Install a specific skill globally
npx skills add https://github.com/SwimmingLiu/easy-skills@<skill-path> -g -y

# Examples:
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/meta/skill-lifecycle -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/image/image-gen-rightcodes -g -y
```

### For Humans (Manual Installation)

1. Clone this repository with its submodules:
```bash
git clone --recurse-submodules https://github.com/SwimmingLiu/easy-skills.git
cd easy-skills
```

If the repository was cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

2. Install a skill to your agent:
```bash
# From local path
npx skills add ./skills/subagent/opencode -g -y

# Or copy the skill directory to your agent's skills folder
cp -r skills/subagent/opencode ~/.agents/skills/
```

Install the external skills with:

```bash
npx skills add ./skills/storyweave/skills/storyweave-html -g -y
npx skills add ./skills/storyweave/skills/storyweave-imagegen -g -y
npx skills add ./skills/storyweave/skills/storyweave-express -g -y
npx skills add ./skills/voiceforge -g -y
```

To update the external repositories to their configured `main` branches:

```bash
git submodule update --remote --merge skills/storyweave skills/voiceforge
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
