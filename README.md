# Easy Skills

A curated collection of reusable AI agent skills for productivity, documentation, image generation, and scientific writing.

## Skills

### Image

- [Image Gen Rightcodes](./skills/image/image-gen-rightcodes/SKILL.md) - RightAPI asynchronous image-generation and editing fallback.

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

### External Skill Repositories

These skills are tracked as Git submodules. Their source remains in the original repositories, so updates do not create a second copy to maintain.

#### [StoryWeave](https://github.com/SwimmingLiu/StoryWeave)

StoryWeave provides three independent skills for 16:9 presentations:

- [StoryWeave HTML](./skills/storyweave/skills/storyweave-html/SKILL.md) - Create editable standalone HTML slides.
- [StoryWeave Imagegen](./skills/storyweave/skills/storyweave-imagegen/SKILL.md) - Create image-based presentation pages and exports.
- [StoryWeave Express](./skills/storyweave/skills/storyweave-express/SKILL.md) - Package existing HTML or image pages for Bento.

#### [Voiceforge](https://github.com/SwimmingLiu/Voiceforge)

- [Voiceforge](./skills/voiceforge/SKILL.md) - Draft, rewrite, polish, and edit Chinese or English reader-facing content.

## Installation

### For Agents

Install a skill globally with the `skills` CLI:

```bash
npx skills add https://github.com/SwimmingLiu/easy-skills@<skill-path> -g -y
```

Examples:

```bash
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/knowledge/knowledge-base -g -y
npx skills add https://github.com/SwimmingLiu/easy-skills@skills/image/image-gen-rightcodes -g -y
```

### For Humans

Clone the repository with its submodules and install from local paths:

```bash
git clone --recurse-submodules https://github.com/SwimmingLiu/easy-skills.git
cd easy-skills
npx skills add ./skills/knowledge/knowledge-base -g -y
```

If the repository was cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
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

Or copy a skill directory to your agent's skills folder:

```bash
cp -r skills/knowledge/knowledge-base ~/.agents/skills/
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
