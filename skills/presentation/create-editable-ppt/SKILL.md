---
name: create-image-ppt
description: Use when a user asks for a PPT, slide deck, presentation, keynote, report, launch, defense, or wants source material turned into concise slides using AI-generated images or HTML plus AI visual assets.
---

# Create Image PPT

**REQUIRED SUB-SKILL:** Use `imagegen` for both modes. Prefer the host's built-in image generation tool. Use the local CLI only when the user explicitly permits it and the local key configuration is present.

This Skill has two deliberate output modes. Both start from the same approved page plan, theme recipe, visual anchors, QA, and Bento-inspired offline document. The difference is who owns the visible words:

| Mode | Imagegen produces | HTML produces | Use when |
|---|---|---|---|
| `image-first` | One complete 16:9 slide image (整页图片), including the approved exact text | Playback controls only | The deck should be extremely concise, visual, keynote-like, or resistant to layout drift |
| `html-image-assisted` | A background panel or illustration with no text, letters, numbers, labels, or logo（无文字视觉素材） | The title, support copy, steps, layout, contrast, and slide structure | The deck needs structured process/comparison/data copy, fast copy changes, or reliable text rendering |

`image-first` is the default for compatibility. Choose `html-image-assisted` when the user values source-level copy changes over a fully rasterized page. In either mode, editing means updating the approved source and regenerating only affected visuals; the audience-facing page does not pretend that raster text is independently editable.

## Workflow

1. **Check inputs.** Read the user's files and identify audience, purpose, language, delivery setting, approximate page count, required output, factual materials, and available images. Do not invent missing facts.
2. **Create the content draft.** Write `outline_draft.json` and `outline_preview.html`. The preview must show the central message, narrative logic (`opening`, `problem`, `insight`, `method`, `action`), page count, and for every page: role, purpose, single claim, exact visible text, evidence/materials, media brief, and transition. Do not call imagegen before the user confirms this draft.
3. **Choose a mode and approve one theme.** Choose `image-first` or `html-image-assisted`, then choose one of the eight deduplicated theme families in `assets/themes/image-themes.json`. Keep the visual anchor consistent across the deck.
4. **Compile prompts.** After approval, write `deck_spec.json`, `generation_manifest.json`, and `imagegen-jobs.jsonl`. In `image-first`, prompts include the closed exact-text list. In `html-image-assisted`, prompts explicitly prohibit text and request negative space for the HTML copy.
5. **Generate images.** Call `imagegen` once per page. Store complete pages under `slides/` for `image-first`; store background/illustration assets under `assets/` for `html-image-assisted`. Reuse user-provided or traced assets when they carry facts. Remind users to configure image-generation keys locally when the CLI is needed; never print key values.
6. **Review and retry.** Check every page for text accuracy, claim fidelity, role-specific composition, image subject/crop, theme consistency, contrast, and unwanted text. Retry only failed pages with a revised prompt.
7. **Render and QA.** `render` selects the renderer from `deck_spec.json`: an image-only player for `image-first`, or an HTML copy/layout renderer for `html-image-assisted`. `qa` performs content, manifest, asset, and missing-image checks. Run browser visual checks when Playwright is available; report degraded checks instead of claiming visual QA.
8. **Bundle or export.** `bundle` creates a single offline HTML file whose JSON block is the source of truth and whose generated assets are embedded as data URIs. `export` can also produce HTML, PNG, PDF, or a screenshot-based PPTX.

内容草稿必须先明确**中心含义**和**叙事逻辑**；**草稿未确认时不得调用生图**。

## Commands

Run these from this Skill directory:

```bash
node scripts/ppt.mjs draft <project-dir> --title "标题"
node scripts/ppt.mjs approve <project-dir> --theme business-minimal --mode image-first
# or: --mode html-image-assisted
node scripts/ppt.mjs prompts <project-dir> --model gpt-image-2 --size 2048x1152 --quality medium
# run imagegen-jobs.jsonl with imagegen, then place outputs under slides/ or assets/ according to the manifest
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
- `generation_manifest.json`: prompt, model, output path, attempt count, status, and error for each page.
- `slides/`: generated full-slide PNGs for `image-first`.
- `assets/`: generated background panels or illustrations for `html-image-assisted`.
- `index.html`: offline deck driven by the same slide manifest; it selects the mode-specific renderer.
- `dist/presentation.image-ppt.html` or `dist/presentation.html-image-assisted.html`: optional Bento-inspired single-file bundle with embedded JSON and image assets.
- `qa_report.json` and `dist/export-report.json`: review findings and export evidence.

## Bento-inspired document contract

The bundle keeps a plaintext `<script type="application/image-ppt+json" id="image-ppt-doc">` block as the source of truth. It embeds image assets as `data:` URIs, escapes `<` before embedding JSON, and includes no remote runtime or asset URL. In `image-first`, the runtime places each complete page image on the canvas. In `html-image-assisted`, it reads the visual asset plus `exact_text` and builds the copy/layout in HTML. AI or a host integration may modify the JSON/manifest and regenerate a page; the bundle does not pretend that raster text is independently editable.

Each slide carries a stable `id`, `visual_anchor_id`, `continuity_group`, `transition`, `claim`, and `speaker_notes`. Stable metadata preserves narrative continuity and presenter transitions even though page pixels are regenerated as a whole.

## Content and visual rules

- Keep one claim per page. Cover and closing pages normally have one title plus one supporting line; process, comparison, and data pages use only the labels needed to explain the claim.
- Classify material before prompting: `image`, `flow`, `comparison`, `table`, `chart`, or `claim`. Use the matching visual representation; never turn precise user data into an invented illustration.
- Exact visible text is a closed list. The model must not add labels, captions, fake citations, numbers, logos, watermarks, or UI chrome.
- In `html-image-assisted`, the visual prompt has no exact-text section: the image must contain no text-like glyphs. All visible words come from the approved HTML source.
- Prefer user assets, then traceable assets, then AI concept imagery. Mark provenance in the manifest.
- Keep the selected theme's palette, typography, composition, and anchors consistent. Do not mix theme recipes page by page unless the user explicitly asks for a multi-theme comparison.
- Favor a small number of strong visual elements over dense cards, long paragraphs, or decorative explanations.

## Themes

`business-minimal`, `editorial`, `swiss-grid`, `launch-tech`, `data-consulting`, `academic`, `brand-bold`, and `premium-dark` are intentionally distinct families. Their recipes are derived from the referenced PPT Skills' recurring strengths and deduplicated by composition, not by color alone. See [themes.md](references/themes.md).

## Failure handling

- Missing or unreadable upload: list the missing path, continue with readable material, and mark unsupported claims as unresolved.
- Insufficient material for the requested page count: propose a shorter deck and identify which pages need evidence; wait for approval before generation.
- No usable image and no safe concept brief: keep the page in `prepared` state with a clear media gap; do not fabricate a factual screenshot, chart, or product result.
- Missing imagegen configuration: stop before generation and tell the user to configure keys locally. Never include a secret in a prompt, log, JSON, or response.
- Generation failure: preserve the prompt and slot, record the error, retry only with a bounded attempt count, and leave the page out of export until it passes.
- Text error, unwanted text, bad crop, or theme drift: mark that page `revise`, revise the prompt or source asset, and regenerate only that page.
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
