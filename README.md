# Easy Skills

A curated collection of reusable AI agent skills for productivity, documentation, diagrams, frontend design, image generation, and scientific writing.

## Skills

### Image

- [Image Gen Rightcodes](./skills/image/image-gen-rightcodes/SKILL.md) - RightAPI asynchronous image-generation and editing fallback.

### Diagrams

- [Draw.io](./skills/diagram/drawio/SKILL.md) - Generate editable draw.io diagrams and export them to PNG, SVG, or PDF.
- [Mermaid Diagrams](./skills/diagram/mermaid-diagrams/SKILL.md) - Create software architecture and process diagrams with Mermaid.
- [Mermaid Correction](./skills/diagram/mermaid-correction/SKILL.md) - Validate, diagnose, and repair Mermaid syntax.

### Knowledge

- [Knowledge Base](./skills/knowledge/knowledge-base/SKILL.md) - Maintain a Codex-native Markdown and Obsidian knowledge base.

### Language

- [Baoyu Translate](./skills/language/baoyu-translate/SKILL.md) - Translate articles and documents with quick, normal, and refined workflows.

### Markdown

- [Baoyu Format Markdown](./skills/markdown/baoyu-format-markdown/SKILL.md) - Format plain text and Markdown documents.
- [Baoyu Markdown to HTML](./skills/markdown/baoyu-markdown-to-html/SKILL.md) - Convert Markdown to styled, WeChat-compatible HTML.

### Scientific Writing

- [Check AI Write](./skills/scientific/check-ai-write/SKILL.md) - Detect and reduce common AI-writing patterns.
- [Correct Wrong Words](./skills/scientific/correct-wrong-words/SKILL.md) - Check and correct Chinese and English typos while protecting technical terms.
- [Paper Rewrite](./skills/scientific/paper-rewrite/SKILL.md) - Rewrite and polish academic papers.

### Frontend

Selected frontend skills adapted from the [Impeccable](https://github.com/pbakaus/impeccable) design language and command set.

| Skill | Purpose |
| --- | --- |
| [Adapt](./skills/frontend/adapt/SKILL.md) | Adapt interfaces across devices and screen sizes. |
| [Animate](./skills/frontend/animate/SKILL.md) | Add purposeful animation and motion. |
| [Audit](./skills/frontend/audit/SKILL.md) | Audit accessibility, performance, theming, and responsive behavior. |
| [Bolder](./skills/frontend/bolder/SKILL.md) | Make safe or bland designs more expressive. |
| [Clarify](./skills/frontend/clarify/SKILL.md) | Improve UX copy, labels, and error messages. |
| [Colorize](./skills/frontend/colorize/SKILL.md) | Add strategic color to monochromatic interfaces. |
| [Critique](./skills/frontend/critique/SKILL.md) | Review UX hierarchy, information architecture, and visual quality. |
| [Delight](./skills/frontend/delight/SKILL.md) | Add personality and memorable interaction details. |
| [Distill](./skills/frontend/distill/SKILL.md) | Remove unnecessary complexity from a design. |
| [Extract](./skills/frontend/extract/SKILL.md) | Extract reusable components, tokens, and patterns. |
| [Harden](./skills/frontend/harden/SKILL.md) | Improve error handling, i18n, overflow, and edge-case behavior. |
| [Onboard](./skills/frontend/onboard/SKILL.md) | Design onboarding flows, empty states, and first-run experiences. |
| [Optimize](./skills/frontend/optimize/SKILL.md) | Improve frontend loading, rendering, and bundle performance. |
| [Polish](./skills/frontend/polish/SKILL.md) | Perform a final pass on alignment, spacing, and visual details. |
| [Quieter](./skills/frontend/quieter/SKILL.md) | Reduce visual intensity while preserving design quality. |

## Installation

### For Agents

Install a skill globally with the `skills` CLI:

```bash
npx skills add https://github.com/SwimmingLiu/easy-skills@<skill-path> -g -y
```

Examples:

```bash
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/frontend/polish -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/knowledge/knowledge-base -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/image/image-gen-rightcodes -g -y
```

### For Humans

Clone the repository and install from a local path:

```bash
git clone https://github.com/SwimmingLiu/easy-skills.git
cd easy-skills
npx skills add ./skills/frontend/polish -g -y
```

Or copy a skill directory to your agent's skills folder:

```bash
cp -r skills/frontend/polish ~/.agents/skills/
```

### Verify Installation

```bash
npx skills list
```

Each skill contains a detailed `SKILL.md` with usage instructions, examples, and configuration details.

## Contributing

Contributions are welcome. Please open an issue or pull request with a clear description of the proposed change.

## License

This project is licensed under the terms specified in [LICENSE](LICENSE).
