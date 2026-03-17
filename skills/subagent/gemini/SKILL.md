---
name: gemini
description: Launch the Gemini TUI inside a dedicated tmux session for project-scoped interactive work. Use when you want a persistent Gemini terminal UI attached to a target repository, with prompt handoff handled by a wrapper script and explicit machine-readable session metadata.
---

# Gemini tmux launcher

Use this skill to start the real `gemini` TUI inside a fresh tmux session.

## Follow this workflow

1. Run `scripts/run_gemini_tmux.sh` with the task text.
2. Capture the printed metadata, especially `SESSION_NAME`.
3. Attach with `tmux attach -t <SESSION_NAME>` when interactive work is needed.
4. Paste the prepared task text from the tmux buffer into Gemini.
5. Monitor progress with normal tmux commands such as `tmux capture-pane`.

## Run the script

```bash
bash ./scripts/run_gemini_tmux.sh "<task>" [working_dir] [session_name]
```

Arguments:
- `task`: Required. The instruction to give Gemini.
- `working_dir`: Optional. Defaults to the current working directory.
- `session_name`: Optional. Defaults to `gemini-<timestamp>`.

## What the script does

- Verifies that `gemini` and `tmux` are available.
- Verifies that the target working directory exists.
- Creates a skill-local `.tmp/tmux` directory for prompt, runner, metadata, and log files.
- Writes the task text to a prompt file.
- Creates a runner script that starts the real `gemini` TUI in the target directory.
- Starts a detached tmux session.
- Copies the task text into the tmux paste buffer for reliable handoff.
- Prints machine-readable metadata so callers can attach or inspect later.

## Expected output

On success, the script prints:

- `SESSION_NAME`
- `WORKDIR`
- `PROMPT_FILE`
- `RUNNER_FILE`
- `LOG_FILE`
- `CURRENT_COMMAND`
- `STATUS`

## Exit codes

The script uses explicit exit codes so callers can distinguish setup failures.

- `0`: Success. The tmux session is ready and the prompt text is staged in the tmux buffer.
- `1`: Invalid invocation or missing required arguments.
- `2`: Failed to create or write required local files.
- `3`: `gemini` is not available in `PATH`.
- `4`: `tmux` is not available in `PATH`.
- `5`: The target working directory does not exist.
- `6`: The requested tmux session name already exists.
- `7`: The tmux session could not be created or validated.
- `8`: Prompt handoff to the tmux buffer failed.

## Operational notes

- Keep instructions and session metadata in English.
- This skill is intentionally interactive. It launches the real Gemini terminal UI, not a one-shot CLI wrapper.
- The wrapper prepares the task text in the tmux buffer, but you still need to paste it into the Gemini UI.
- Clean up stale tmux sessions and skill-local `.tmp/tmux` files when they are no longer needed.
- For deterministic non-interactive automation, use a one-shot CLI-style skill instead of this one.
