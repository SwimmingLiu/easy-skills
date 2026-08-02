---
name: create-image-ppt
description: Use when a user asks for a concise PPT, slide deck, presentation, keynote, report, launch, defense, or wants source material turned into a themed presentation.
---

# Create Image PPT

**REQUIRED SUB-SKILL:** Use `imagegen` only for the `image-first` mode. Prefer the host's built-in image generation tool. Use the local CLI only when the user explicitly permits it and the local key configuration is present.

This Skill has two mutually exclusive output modes. Both use the same approved page plan, theme recipe, visual anchors, QA, and Bento-inspired offline document. The difference is who owns the page pixels:

| Mode | Page owner | Image generation | Use when |
|---|---|---|---|
| `image-first` | One complete raster image per page（整页图片） | `imagegen` creates the full 16:9 slide, including the approved exact text | The deck should be concise, visual, keynote-like, and resistant to layout drift |
| `pure-html` | HTML owns all text, layout, and visual structure（纯 HTML） | None; decorative motifs are CSS/HTML only | The user needs fast source-level copy changes, structured process/comparison/data pages, and no image dependency |

Do not combine the modes within one deck. `pure-html` 不调用 imagegen，不创建图片槽位，也不插入 AI 背景或插图。`image-first` keeps the audience-facing page as a complete image; HTML supplies playback controls only. Updating either mode means editing the approved source and regenerating or rerendering only the affected pages.

## Workflow

1. **Check inputs.** Identify audience, purpose, language, delivery setting, approximate page count, required output, factual materials, and available images. Do not invent missing facts.
2. **Create the content draft.** Write `outline_draft.json` and `outline_preview.html`. The preview must show the **中心含义** and **叙事逻辑** (`opening`, `problem`, `insight`, `method`, `action`), page count, and for every page: role, purpose, single claim, exact visible text, evidence/materials, media brief, and transition. **草稿未确认时不得调用生图。**
3. **Choose one mode and one theme.** Choose `image-first` or `pure-html`, then choose one of the eight deduplicated theme families in `assets/themes/image-themes.json`. Keep the visual anchor consistent across the deck.
4. **Compile the source.** After approval, write `deck_spec.json` and `generation_manifest.json`. `image-first` also writes `imagegen-jobs.jsonl`; `pure-html` writes an empty jobs file and marks every page `pass` because no image generation is required.
5. **Generate or render.** For `image-first`, call `imagegen` once per page and store complete pages under `slides/`. Remind users to configure image-generation keys locally when this path is needed; never print key values. For `pure-html`, render immediately from the approved text and theme; do not create `slides/` or `assets/`.
6. **Review and retry.** Check every page for text accuracy, claim fidelity, role-specific composition, contrast, theme consistency, and unwanted overflow. Retry only failed image pages; revise the source and rerender pure HTML pages.
7. **Render and QA.** `render` selects the mode-specific renderer. `qa` performs content, manifest, missing-file, page-count, and role-specific checks. Run browser visual checks when Playwright is available; report degraded checks instead of claiming visual QA.
8. **Bundle or export.** `bundle` creates a single offline HTML file with the JSON source of truth. `image-first` embeds image data URIs; `pure-html` embeds no image data. `export` can produce HTML, PNG, PDF, or a screenshot-based PPTX.

## Commands

Run these from this Skill directory:

```bash
node scripts/ppt.mjs draft <project-dir> --title "标题"
node scripts/ppt.mjs approve <project-dir> --theme business-minimal --mode image-first
# or: --mode pure-html
node scripts/ppt.mjs prompts <project-dir> --model gpt-image-2 --size 2048x1152 --quality medium
# image-first: run imagegen-jobs.jsonl with imagegen, then place outputs under slides/
# pure-html: the jobs file is intentionally empty; continue directly to render
node scripts/ppt.mjs render <project-dir>
node scripts/ppt.mjs qa <project-dir> --json
node scripts/ppt.mjs bundle <project-dir>
node scripts/ppt.mjs export <project-dir> --format pptx
node scripts/ppt.mjs doctor --json
```

## Project contract

- `outline_draft.json`: user-reviewable content plan; generation is blocked until it is approved.
- `outline_preview.html`: compact review surface for the central message, narrative, and page-by-page claims.
- `deck_spec.json`: approved content, mode, theme, visual anchors, transitions, and speaker notes; JSON source for generation.
- `generation_manifest.json`: mode, output path, attempt count, status, and error for each page.
- `slides/`: generated complete slide PNGs for `image-first` only.
- `assets/`: not used by `pure-html`; no AI background or illustration is inserted.
- `index.html`: offline deck driven by the same manifest; it selects the mode-specific renderer.
- `dist/presentation.image-ppt.html` or `dist/presentation.pure-html.html`: optional Bento-inspired single-file bundle.
- `qa_report.json` and `dist/export-report.json`: review findings and export evidence.

## Bento-inspired document contract

The bundle keeps a plaintext `<script type="application/image-ppt+json" id="image-ppt-doc">` block as the source of truth, escapes `<` before embedding JSON, and includes no remote runtime or asset URL. In `image-first`, each slide references an embedded complete page image. In `pure-html`, `assets` is `{}` and each slide contains `exact_text`; the runtime rebuilds the same concise HTML structure and CSS motif.

Each slide carries a stable `id`, `visual_anchor_id`, `continuity_group`, `transition`, `claim`, and `speaker_notes`. Stable metadata preserves narrative continuity even when a page is regenerated or rerendered.

## Content and visual rules

- Keep one claim per page. Cover and closing pages normally have one title plus one supporting line; process, comparison, and data pages use only the labels needed to explain the claim.
- Classify material before prompting: `image`, `flow`, `comparison`, `table`, `chart`, or `claim`. Use the matching representation; never turn precise user data into an invented illustration.
- Exact visible text is a closed list. `image-first` must render it verbatim and must not add labels, fake citations, numbers, logos, watermarks, or UI chrome. `pure-html` renders it through text nodes from the approved JSON.
- Keep the selected theme's palette, typography, composition, and anchors consistent. Do not mix theme recipes page by page unless the user explicitly asks for a multi-theme comparison.
- Favor a small number of strong visual elements over dense cards, long paragraphs, or decorative explanations.

## Themes

`business-minimal`, `editorial`, `swiss-grid`, `launch-tech`, `data-consulting`, `academic`, `brand-bold`, and `premium-dark` are intentionally distinct families. Their recipes combine recurring strengths from the referenced PPT Skills and are deduplicated by composition, not by color alone. See [themes.md](references/themes.md).

## Failure handling

- Missing or unreadable upload: list the missing path, continue with readable material, and mark unsupported claims as unresolved.
- Insufficient material for the requested page count: propose a shorter deck and identify which pages need evidence; wait for approval before generation.
- `image-first` without a usable image brief or required source asset: keep the page `prepared` and report the media gap; do not fabricate a factual screenshot, chart, or product result.
- Missing imagegen configuration: stop before `image-first` generation and tell the user to configure keys locally. Never include a secret in a prompt, log, JSON, or response. `pure-html` remains available because it has no image dependency.
- Generation failure: preserve the prompt and slot, record the error, retry only with a bounded attempt count, and leave the page out of export until it passes.
- Text error, bad crop, theme drift, overflow, or role mismatch: mark that page `revise`, revise the source or prompt, and regenerate or rerender only that page.
- Optional export dependency missing: keep HTML available and report the unavailable PDF, PNG, or PPTX adapter.
- Browser QA unavailable: run semantic and manifest checks, label geometry checks as `degraded`, and do not claim a visual pass.

## Review gate

Review differs by page role: data checks source and units; process checks order and responsibility; comparison checks aligned dimensions; image pages check subject and crop; quote pages check attribution; cover and closing pages check message and action. Export is allowed only when the outline is valid, every active page is `generated` or `pass`, all blocking findings are resolved, and the final HTML/bundle reopens with the expected page count.

## References

- [workflow.md](references/workflow.md): intake, draft confirmation, generation, retry, and review flow.
- [architecture.md](references/architecture.md): JSON source of truth, renderer boundary, and Bento-inspired bundle.
- [content.md](references/content.md): concise page roles and evidence policy.
- [assets.md](references/assets.md): imagegen, provenance, and factual-asset rules.
- [qa-export.md](references/qa-export.md): semantic, visual, and export checks.
