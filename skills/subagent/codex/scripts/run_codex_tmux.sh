#!/usr/bin/env bash
set -euo pipefail

EXIT_USAGE=1
EXIT_IO=2
EXIT_CODEX_MISSING=3
EXIT_TMUX_MISSING=4
EXIT_WORKDIR_MISSING=5
EXIT_SESSION_EXISTS=6
EXIT_LAUNCH_FAILED=7
EXIT_HANDOFF_FAILED=8

fail() {
  local code="$1"
  shift
  echo "ERROR: $*" >&2
  exit "$code"
}

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"<task>\" [working_dir] [session_name]" >&2
  exit "$EXIT_USAGE"
fi

TASK="$1"
WORKDIR="${2:-$(pwd)}"
SESSION_NAME="${3:-codex-$(date +%Y%m%d-%H%M%S)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$SKILL_DIR/.tmp/tmux"

command -v codex >/dev/null 2>&1 || fail "$EXIT_CODEX_MISSING" "codex not found in PATH"
command -v tmux >/dev/null 2>&1 || fail "$EXIT_TMUX_MISSING" "tmux not found in PATH"
[[ -d "$WORKDIR" ]] || fail "$EXIT_WORKDIR_MISSING" "working directory does not exist: $WORKDIR"
mkdir -p "$OUTPUT_DIR" || fail "$EXIT_IO" "unable to create output directory: $OUTPUT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
SAFE_SLUG="$(printf '%s' "$TASK" | tr -cd '[:alnum:]_-' | cut -c1-32)"
[[ -n "$SAFE_SLUG" ]] || SAFE_SLUG="task"
PROMPT_FILE="$OUTPUT_DIR/prompt_${STAMP}_${SAFE_SLUG}.txt"
RUNNER_FILE="$OUTPUT_DIR/runner_${STAMP}_${SAFE_SLUG}.sh"
LOG_FILE="$OUTPUT_DIR/session_${STAMP}_${SAFE_SLUG}.log"
META_FILE="$OUTPUT_DIR/meta_${STAMP}_${SAFE_SLUG}.txt"

cat > "$PROMPT_FILE" <<EOF
$TASK
EOF

cat > "$RUNNER_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$WORKDIR"
printf 'Launching Codex TUI in %s\n' "$WORKDIR"
printf 'Prompt file: %s\n' "$PROMPT_FILE"
printf 'The task text has been copied to the tmux paste buffer.\n'
printf 'Paste it into Codex with Ctrl-Shift-V, Shift-Insert, or tmux paste-buffer.\n\n'
exec codex 2>&1 | tee -a "$LOG_FILE"
EOF
chmod +x "$RUNNER_FILE" || fail "$EXIT_IO" "unable to mark runner executable: $RUNNER_FILE"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  fail "$EXIT_SESSION_EXISTS" "tmux session already exists: $SESSION_NAME"
fi

tmux new-session -d -s "$SESSION_NAME" -c "$WORKDIR" "bash '$RUNNER_FILE'" >/dev/null 2>&1 || fail "$EXIT_LAUNCH_FAILED" "failed to create tmux session: $SESSION_NAME"
sleep 1
CURRENT_COMMAND="$(tmux display-message -p -t "$SESSION_NAME" '#{pane_current_command}' 2>/dev/null || true)"
[[ -n "$CURRENT_COMMAND" ]] || fail "$EXIT_LAUNCH_FAILED" "tmux session started but pane command could not be read"

tmux set-buffer -- "$(cat "$PROMPT_FILE")" || fail "$EXIT_HANDOFF_FAILED" "failed to copy task text into tmux buffer"

cat > "$META_FILE" <<EOF
SESSION_NAME: $SESSION_NAME
WORKDIR: $WORKDIR
PROMPT_FILE: $PROMPT_FILE
RUNNER_FILE: $RUNNER_FILE
LOG_FILE: $LOG_FILE
CURRENT_COMMAND: $CURRENT_COMMAND
STATUS: ready
EOF

cat "$META_FILE"
exit 0
