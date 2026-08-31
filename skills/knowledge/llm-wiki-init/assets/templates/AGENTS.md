# Knowledge Base Maintenance Protocol

This repository is a local, source-backed LLM Wiki. Preserve original material in `raw/`, continuously compile reusable knowledge into `wiki/`, and keep task deliverables in `outputs/`.

## Privacy First

- Treat everything in this repository as private unless the user explicitly says it may be shared.
- Never publish, upload, email, push, or paste repository content into an external service without explicit approval.
- Never store passwords, API keys, access tokens, private keys, session cookies, full identity-document numbers, or other authentication secrets here.
- Before sharing a copy, run `bash scripts/privacy_scan.sh` and review the result manually.
- Do not assume that a summary is safe to share merely because the original file was removed; summaries and indexes can still contain private facts.

## Directory Roles

- `raw/`: original sources and first-hand records. Preserve source meaning; do not replace the only copy of a source with a rewrite.
- `wiki/`: the compiled, reusable knowledge layer maintained by humans and agents.
- `wiki/sources/`: structured summaries of important individual sources or source batches.
- `wiki/topics/`: evergreen knowledge synthesized across sources.
- `wiki/entities/`: people, organizations, products, projects, models, and events.
- `wiki/analyses/`: reusable answers, comparisons, judgments, and synthesis.
- `wiki/decisions/`: durable choices, trade-offs, reasons, and follow-up actions.
- `wiki/indexes/`: generated catalogs and maintenance indexes.
- `index/`: human-facing Obsidian navigation.
- `outputs/`: articles, reports, translations, outlines, and other deliverables.
- `assets/`: local images and attachments.
- `skills/`: optional, shareable agent Skills used by the ingestion workflow.
- `scripts/`: local index, lint, installation, and privacy-check utilities.

## Required Reading Order

For any knowledge question or maintenance task:

1. Read `wiki/index.md`.
2. Read `wiki/overview.md`.
3. Search exact terms, aliases, entities, and source names with `rg`.
4. Read the relevant topic, source, entity, analysis, and decision pages.
5. Separate facts, synthesis, inference, and recommendations in the answer.

Simple file operations that do not depend on knowledge content do not require loading the whole Wiki.

## Routing New Material

Use the existing sibling layout when extending a source batch. If a source type is ambiguous, make a conservative choice and record it instead of blocking.

| Material | Destination |
| --- | --- |
| Web article, company blog, or long social article | `raw/articles/` |
| Time-sensitive news | `raw/news/` |
| Academic paper | `raw/papers/` |
| Industry report or whitepaper | `raw/reports/` |
| Single X/Twitter post or thread | `raw/twitter/` |
| Date-based X/Twitter digest | `raw/twitters/` |
| WeChat material | `raw/wechat/` |
| Recording, meeting, or interview | `raw/records/` |
| YouTube transcript | `raw/youtube-transcript/` |
| Xiaoyuzhou transcript | `raw/xiaoyuzhou/` |
| Other video or subtitle material | `raw/video/` |

### Dropped Files and Links

- Audio/video: download temporary media to `tmp/imports/`, transcribe locally, proofread the transcript, then retain only the useful transcript in the appropriate `raw/` directory. Use the bundled `video-downloader`, `local-audio-transcriber`, and `subtitle-proofreader` Skills when installed.
- Images or scans: save the source under the matching `raw/` directory, run the bundled `image-ocr` Skill, and save an OCR companion Markdown file next to the image. Skip OCR for purely decorative images.
- Documents or web pages: retain the source under the matching `raw/` directory, then continue with the ingest workflow below.
- Do not send private material to third-party OCR, transcription, or summarization services unless the user explicitly approves it.

## Ingest Workflow

For valuable new material:

1. Record the title, author/source, date, URL or local path, source type, and reliability.
2. Create or update a source summary in `wiki/sources/`.
3. Update the relevant topic, entity, or analysis pages; do not leave a standalone summary as the only retrieval path to a durable conclusion.
4. Mark how the material relates to current knowledge: `supports`, `extends`, `contradicts`, `supersedes`, or `opens`.
5. Add meaningful Obsidian links using vault-relative canonical targets.
6. Update `wiki/index.md` when durable navigation changes.
7. Append `wiki/log.md` with the change and any follow-up check.
8. Run `ruby scripts/rebuild_kb_indexes.rb`, then `ruby scripts/kb_lint.rb`.

## Page Conventions

Use Markdown, Obsidian links, and frontmatter:

```yaml
---
title: Page title
type: topic
status: current
date: 2026-01-01
updated: 2026-01-01
tags:
  - example-tag
source:
  - "[[raw/path/to/source]]"
summary: One sentence describing the page's durable value.
---
```

Recommended `type` values: `source`, `topic`, `entity`, `analysis`, `decision`, `index`, `overview`, `log`.

Recommended `status` values: `draft`, `current`, `needs-review`, `stale`, `archived`.

Use lowercase `kebab-case` tags. Put the canonical term and useful aliases in the title, summary, or opening paragraph. A source page should identify its retained evidence and explain its relationship to existing knowledge.

## Obsidian Link Maintenance

- Search before creating a new page; prefer an existing canonical note.
- Link the first natural mention or add a short related-notes section. Do not link every repetition.
- Do not edit raw source text solely to insert links. Put links in source summaries, compiled pages, or deliverables.
- Do not modify a target page solely to create a mechanical reciprocal link; Obsidian already provides backlinks.
- Before finishing an edit, make a final pass for missing meaningful links.

## Retrieval Contract

- High-value Wiki pages require `title`, `type`, `status`, `updated`, canonical `tags`, and a one-sentence `summary`.
- Use `wiki/index.md` for curated entry points, `wiki/indexes/wiki-catalog.md` for complete coverage, `wiki/indexes/tag-index.md` for tag browsing, and `wiki/indexes/output-status.md` for deliverables.
- Do not hand-edit machine-generated indexes. Rebuild them with `ruby scripts/rebuild_kb_indexes.rb`.
- State uncertainty when evidence is thin, stale, or contradictory.
- If an answer will be reused, write it into `wiki/analyses/` or the relevant topic page and log the update.

## Editing and Version-Control Boundaries

- Preserve user-created files and unrelated uncommitted changes.
- Prefer small incremental migrations; record structural changes in `wiki/log.md`.
- Do not delete, overwrite, rename, or bulk-move original material without explicit approval.
- Review `git status` before staging changes and keep commits scoped.
- Do not push or otherwise publish the repository without explicit approval.

