#!/bin/bash

set -euo pipefail

ACK_VAR="OPENCLAW_ALLOW_DIRECT_AGENT_BYPASS"
REASON_VAR="OPENCLAW_DIRECT_AGENT_BYPASS_REASON"

log_error() { printf '[ERROR] %s\n' "$1" >&2; }
log_warn() { printf '[WARN] %s\n' "$1" >&2; }

usage() {
    cat >&2 <<'EOF'
用法:
  OPENCLAW_ALLOW_DIRECT_AGENT_BYPASS=1 \
  OPENCLAW_DIRECT_AGENT_BYPASS_REASON="<why bypass is intentional>" \
  ./scripts/agent-orchestration/direct-exec-bypass.sh <agent-cli> [args...]

示例:
  OPENCLAW_ALLOW_DIRECT_AGENT_BYPASS=1 \
  OPENCLAW_DIRECT_AGENT_BYPASS_REASON="user explicitly requested no worktree/monitoring" \
  ./scripts/agent-orchestration/direct-exec-bypass.sh \
    opencode run "Explain auth flow in @src/auth.ts"
EOF
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

if [[ "${!ACK_VAR:-}" != "1" ]]; then
    log_error "默认必须走 agent-dispatch。仅当用户明确要求绕过 worktree 或 monitoring 时，才设置 ${ACK_VAR}=1。"
    usage
    exit 1
fi

if [[ -z "${!REASON_VAR:-}" ]]; then
    log_error "缺少绕过原因。请设置 ${REASON_VAR} 说明为何这是有意例外。"
    usage
    exit 1
fi

case "$(basename -- "$1")" in
    opencode|gemini|codex|claude)
        ;;
    *)
        log_error "此 helper 仅用于 OpenCode、Gemini、Codex 或 Claude 的直接 CLI 绕过。"
        usage
        exit 1
        ;;
esac

log_warn "已显式绕过 agent-dispatch。原因: ${!REASON_VAR}"
log_warn "工作目录: $PWD"
printf '[WARN] 即将直接执行: ' >&2
printf '%q ' "$@" >&2
printf '\n' >&2

exec "$@"
