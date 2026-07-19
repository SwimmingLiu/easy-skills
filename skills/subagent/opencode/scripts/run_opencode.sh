#!/usr/bin/env bash
set -euo pipefail

EXIT_USAGE=1
EXIT_IO=2
EXIT_OPENCODE_MISSING=3
EXIT_WORKDIR_MISSING=4
EXIT_OPENCODE_RUN=5
EXIT_RESULT_MISSING=6

fail() {
  local code="$1"
  shift
  echo "ERROR: $*" >&2
  exit "$code"
}

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"<task>\" [working_dir] [output_dir]" >&2
  exit "$EXIT_USAGE"
fi

TASK="$1"
WORKDIR="${2:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${3:-$SKILL_DIR/.tmp/opencode-output}"
OPENCODE_TIMEOUT_SECONDS="${OPENCODE_TIMEOUT_SECONDS:-300}"

command -v opencode >/dev/null 2>&1 || fail "$EXIT_OPENCODE_MISSING" "opencode not found in PATH"
[[ -d "$WORKDIR" ]] || fail "$EXIT_WORKDIR_MISSING" "working directory does not exist: $WORKDIR"
mkdir -p "$OUTPUT_DIR" || fail "$EXIT_IO" "unable to create output directory: $OUTPUT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
SAFE_SLUG="$(printf '%s' "$TASK" | tr -cd '[:alnum:]_-' | cut -c1-32)"
[[ -n "$SAFE_SLUG" ]] || SAFE_SLUG="task"
RESULT_FILE="$OUTPUT_DIR/result_${STAMP}_${SAFE_SLUG}.md"
PROMPT_FILE="$OUTPUT_DIR/prompt_${STAMP}_${SAFE_SLUG}.txt"
PRE_RUN_REPORT_SNAPSHOT="$OUTPUT_DIR/reports_before_${STAMP}_${SAFE_SLUG}.txt"
POST_RUN_REPORT_SNAPSHOT="$OUTPUT_DIR/reports_after_${STAMP}_${SAFE_SLUG}.txt"
OPENCODE_LOG_FILE="$OUTPUT_DIR/opencode_${STAMP}_${SAFE_SLUG}.log"

find "$WORKDIR/docs/report" -maxdepth 1 -type f 2>/dev/null | sort > "$PRE_RUN_REPORT_SNAPSHOT" || true

cat > "$PROMPT_FILE" <<EOF2 || fail "$EXIT_IO" "unable to write prompt file: $PROMPT_FILE"
You are running in OpenCode CLI against the project at:
$WORKDIR

Task:
$TASK

Hard requirements:
1. Write your final answer to this exact file path:
   $RESULT_FILE
2. Overwrite the file with the complete final answer in markdown.
3. If the task requires repository output files, create them inside the target repository before finishing.
4. Do not say the task is complete until the required file writes succeed.
5. End your final CLI response with exactly this line:
   RESULT_FILE: $RESULT_FILE
EOF2

OPENCODE_EXIT=0
if ! (cd "$WORKDIR" && timeout "$OPENCODE_TIMEOUT_SECONDS" opencode run "$(cat "$PROMPT_FILE")") > "$OPENCODE_LOG_FILE" 2>&1; then
  OPENCODE_EXIT=$?
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  find "$WORKDIR/docs/report" -maxdepth 1 -type f 2>/dev/null | sort > "$POST_RUN_REPORT_SNAPSHOT" || true
  NEW_REPORTS="$(comm -13 "$PRE_RUN_REPORT_SNAPSHOT" "$POST_RUN_REPORT_SNAPSHOT" || true)"
  LATEST_REPORT="$(printf '%s\n' "$NEW_REPORTS" | sed '/^$/d' | tail -n 1)"

  if [[ -z "$LATEST_REPORT" ]]; then
    LATEST_REPORT="$(find "$WORKDIR/docs/report" -maxdepth 1 -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)"
  fi

  if [[ -n "$LATEST_REPORT" && -s "$LATEST_REPORT" ]]; then
    {
      echo "# OpenCode run summary"
      echo
      echo "- Task: $TASK"
      echo "- Workdir: $WORKDIR"
      echo "- Result mode: wrapper-fallback"
      echo "- OpenCode exit: $OPENCODE_EXIT"
      echo "- OpenCode log: $OPENCODE_LOG_FILE"
      echo "- Primary artifact: $LATEST_REPORT"
      echo
      echo "## Artifact preview"
      echo
      sed -n '1,200p' "$LATEST_REPORT"
    } > "$RESULT_FILE" || fail "$EXIT_IO" "unable to synthesize fallback result file: $RESULT_FILE"
  fi
fi

if [[ ! -s "$RESULT_FILE" && "$OPENCODE_EXIT" -ne 0 ]]; then
  fail "$EXIT_OPENCODE_RUN" "opencode run failed with exit code $OPENCODE_EXIT"
fi

[[ -s "$RESULT_FILE" ]] || fail "$EXIT_RESULT_MISSING" "result file was not created or is empty: $RESULT_FILE"

cat <<EOF2
WORKDIR: $WORKDIR
RESULT_FILE: $RESULT_FILE
OUTPUT_DIR: $OUTPUT_DIR
OPENCODE_LOG_FILE: $OPENCODE_LOG_FILE
OPENCODE_EXIT: $OPENCODE_EXIT
STATUS: success
EOF2

exit 0
