---
name: opencode-cli
description: Run OpenCode in a deterministic one-shot workflow against a local project and capture the final markdown result at a predictable file path. Use when you need non-interactive OpenCode automation, explicit machine-readable metadata, and stable exit codes instead of a tmux-based TUI session.
---

# OpenCode deterministic runner

Use this skill to execute a one-shot OpenCode task against a project and save the final answer to a deterministic markdown file.

## Follow this workflow

1. Run `scripts/run_opencode.sh` with the task text.
2. Capture the printed `RESULT_FILE` path.
3. Read the file at `RESULT_FILE` after the script exits successfully.
4. Treat the file contents as the source of truth.

## Run the script

```bash
bash ./scripts/run_opencode.sh "<task>" [working_dir] [output_dir]
```

Arguments:
- `task`: Required. The instruction for OpenCode.
- `working_dir`: Optional. Defaults to the current working directory.
- `output_dir`: Optional. Defaults to `.tmp/opencode-output` inside the skill directory.

Environment:
- `OPENCODE_TIMEOUT_SECONDS`: Optional. Defaults to `300`.

## What the script does

- Creates the output directory if needed.
- Generates a deterministic result file path.
- Builds a prompt that tells OpenCode to write the final answer to that exact path.
- Runs `opencode run` in the target project directory with a bounded timeout.
- Synthesizes a wrapper result file from repository artifacts when OpenCode skips the requested `RESULT_FILE` write.
- Prints machine-readable metadata for downstream automation, including the OpenCode log path and exit code.

## Expected output

On success, the script prints:

- `WORKDIR`
- `RESULT_FILE`
- `OUTPUT_DIR`
- `OPENCODE_LOG_FILE`
- `OPENCODE_EXIT`
- `STATUS`

Read `RESULT_FILE` after success.

## Exit codes

The script uses explicit exit codes so callers can distinguish different failure modes.

- `0`: OpenCode completed successfully and a non-empty result file is available. The result file may be written directly by OpenCode or synthesized by the wrapper as a fallback.
- `1`: Invalid invocation or missing required arguments.
- `2`: Failed to create required directories or prompt or result files.
- `3`: `opencode` is not available in `PATH`.
- `4`: The target working directory does not exist.
- `5`: OpenCode execution failed and the wrapper could not recover from existing repository artifacts.
- `6`: OpenCode finished without producing a usable result file and the wrapper could not synthesize one.

## Operational notes

- Keep instructions and status-code descriptions in English.
- Prefer this deterministic runner over interactive TUI flows when automation or validation matters.
- Ask OpenCode to save any additional project artifacts, such as reports under `docs/report`, inside the target repository.
- Use the wrapper fallback when repository artifacts exist but OpenCode skips the requested `RESULT_FILE` write.
- Read the generated project artifact separately when the task requests repository changes in addition to the result summary.
