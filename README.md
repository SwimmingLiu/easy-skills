# Easy Skills

🚀 A curated collection of high-quality AI agent skills for enhanced productivity and automation.

## Overview

Easy Skills provides a set of powerful, ready-to-use agent skills designed to streamline your workflow. Each skill is carefully crafted to handle specific tasks efficiently, from code analysis to academic writing assistance.

## Skills

### 🤖 Subagent Skills

AI-powered subagent integrations with automatic fallback support.

#### [Gemini](./skills/subagent/gemini/SKILL.md)
Execute Gemini CLI for AI-powered code analysis and generation with automatic fallback to OpenCode when rate limits or authentication issues occur.

**Features:**
- Automatic fallback to OpenCode paper agent
- Support for multiple Gemini models
- Cross-platform compatibility
- Output saving and session management

#### [Codex](./skills/subagent/codex/SKILL.md)
Execute Codex CLI for code analysis, refactoring, and automated code changes with automatic fallback support.

**Features:**
- Priority strategy: OpenCode Agent first, Codex CLI fallback
- Session resumption support
- File reference via `@` syntax
- Structured JSON output parsing

### 📚 Scientific Skills

Academic writing and research assistance tools.

#### [Paper Rewrite](./skills/scientific/paper-rewrite/SKILL.md)
论文降重与学术润色工具，支持深度降重（同义词替换、句式变换、语义重组）和学术润色（语法修正、风格提升、逻辑优化）。

**Features:**
- Deep paraphrasing with semantic preservation
- Academic style enhancement
- Sentence structure transformation
- Professional vocabulary upgrade

#### [Check AI Write](./skills/scientific/check-ai-write/SKILL.md)
去除文本中的 AI 生成痕迹，使文字更自然、更有人味。基于维基百科的"AI 写作特征"综合指南。

**Features:**
- Detect and fix AI writing patterns
- Inject personality and authenticity
- Quality scoring system
- Comprehensive pattern library

#### [Correct Wrong Words](./skills/scientific/correct-wrong-words/SKILL.md)
多格式文本错别字检测与修正工具，支持纯文本、Markdown、LaTeX 等格式。

**Features:**
- Multi-format support (Markdown, LaTeX, plain text)
- Bilingual error detection (Chinese & English)
- Technical term protection
- Structured output with correction records

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
