---
name: image-gen-rightcodes
description: Use RightAPI's asynchronous image-generation CLI as an explicit fallback for image generation or editing when the built-in image tool fails or the user requests CLI/API execution. Supports text-to-image, reference-image editing, JSONL batches, task polling, URL/base64 results, and redacted diagnostics.
---

# Image Gen Rightcodes

Use this skill when the user explicitly chooses the CLI/API path, when the task specifically
requires the RightAPI protocol, or when the built-in image tool fails under the user's documented
imagegen routing rule. The default image-generation path remains the built-in image tool.

## Core Contract

- Read configuration from the `codex image gen key` section of `~/.zshrc`.
- Require `OPENAI_SUB_BASE_URL`, `OPENAI_SUB_KEY`, and `OPENAI_SUB_IMAGE_MODEL`.
- Treat `OPENAI_SUB_IMAGE_VIP_MODEL` as an explicit higher-quality model choice, not an automatic
  fallback.
- Submit to `{OPENAI_SUB_BASE_URL}/v1/images/generations` with `"async": true`.
- Poll the site-level `/v1/tasks/{task_id}` endpoint. Remove the `/draw` suffix from the configured
  base URL when constructing the task endpoint.
- Accept completed results from `data[].url` or `data[].b64_json`; accept a completed response with
  image data even when the gateway omits `status`.
- Never print API keys, bearer tokens, signed URLs, or reference-image base64 data.

Do not map the RightAPI variables to `OPENAI_BASE_URL` and run the bundled OpenAI `image_gen.py`.
That CLI expects a synchronous Images response, while RightAPI returns a task first. Use the
bundled `scripts/rightapi_imagegen.py` instead.

## Workflow

1. Load the shell configuration without printing values:

   ```bash
   source ~/.zshrc
   ```

2. Locate this skill directory and set a task-specific variable:

   ```bash
   RIGHTCODES_SKILL_DIR="${IMAGE_GEN_RIGHTCODES_SKILL_DIR:-${CODEX_HOME:-$HOME/.codex}/skills/image-gen-rightcodes}"
   RIGHTCODES_CLI="$RIGHTCODES_SKILL_DIR/scripts/rightapi_imagegen.py"
   ```

3. Run a dry-run before a live request. Confirm that the payload contains `"async": true`, the
   intended model, the intended size, and the expected output path:

   ```bash
   python3 "$RIGHTCODES_CLI" generate \
     --model "$OPENAI_SUB_IMAGE_MODEL" \
     --prompt "dry run" \
     --size 1:1 \
     --out output/imagegen/dry-run.png \
     --dry-run
   ```

4. Run the smallest useful live request, then increase resolution or `n` only when required:

   ```bash
   python3 "$RIGHTCODES_CLI" generate \
     --model "$OPENAI_SUB_IMAGE_MODEL" \
     --prompt "A single red apple on a clean white studio background" \
     --size 1:1 \
     --out output/imagegen/apple.png
   ```

5. Verify that the output exists and is a readable raster image. Report the saved path and the
   final prompt to the user.

## Operations

Use `generate` for new images. Use repeated `--image` flags when reference images should guide
generation:

```bash
python3 "$RIGHTCODES_CLI" generate \
  --image reference.png \
  --prompt "Keep the subject and composition; change the style to cyberpunk" \
  --size 16:9 \
  --out output/imagegen/cyberpunk.png
```

Use `edit` when the input image is the edit target. RightAPI still uses the Images generations
endpoint and receives the input as `image: [data URL, ...]`:

```bash
python3 "$RIGHTCODES_CLI" edit \
  --image input.png \
  --prompt "Change only the background; keep the subject and edges unchanged" \
  --out output/imagegen/edited.png
```

Use `generate-batch` with one JSON object per line, each containing at least `prompt`:

```bash
python3 "$RIGHTCODES_CLI" generate-batch \
  --input prompts.jsonl \
  --out-dir output/imagegen/batch
```

Use `--image-size 2K` or `--image-size 4K` only with a model and account that support the
RightAPI `imageSize` field. Pass `--model "$OPENAI_SUB_IMAGE_VIP_MODEL"` explicitly when the
user requests the configured VIP model.

Use `--poll-interval` and `--poll-timeout` for slow queues. The adapter retries transient polling
HTTP, TLS, and connection failures until the polling deadline.

## Unsupported Options

Do not silently translate unsupported OpenAI-only options. The adapter rejects `--background
transparent`, `--mask`, and `--output-compression`. It warns and ignores `--quality`,
`--moderation`, and `--input-fidelity` because the documented RightAPI Images endpoint does not
define equivalent fields. Do not claim native transparency through this skill.

## Shell Callback

Prefer an existing `imagegen-cli` callback when it already points to this skill's script. If no
callback exists, configure it explicitly rather than creating a second fallback chain:

```zsh
imagegen-cli() {
  local skill_dir="${IMAGE_GEN_RIGHTCODES_SKILL_DIR:-${CODEX_HOME:-$HOME/.codex}/skills/image-gen-rightcodes}"
  local runner="$skill_dir/scripts/rightapi_imagegen.py"
  if [[ ! -f "$runner" ]]; then
    print -u2 "imagegen-cli: Rightcodes adapter not found: $runner"
    return 66
  fi
  command python3 "$runner" "$@"
}
```

Do not add fallback credentials, retry them against another provider, or copy literal key values
into this skill, shell history, prompts, logs, or generated files.

For endpoint shapes, response examples, and configuration troubleshooting, read
[references/rightapi.md](references/rightapi.md). The deterministic implementation lives in
[scripts/rightapi_imagegen.py](scripts/rightapi_imagegen.py).
