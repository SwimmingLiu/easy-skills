#!/bin/bash
# spawn-agent.sh - 创建独立 worktree + tmux session 并启动 Agent
# 用法: ./spawn-agent.sh <task-id> <agent-type> [model] <prompt>
# 示例: ./spawn-agent.sh feat-templates codex "实现模板系统"
# 示例: ./spawn-agent.sh feat-templates codex gpt-5-codex "实现模板系统"

set -euo pipefail

TASK_ID="${1:-}"
AGENT_TYPE="${2:-}"

# 判断第3个参数是 model 还是 prompt
# 如果有第4个参数，则第3个是 model，第4个是 prompt
# 否则第3个是 prompt，model 使用默认值
if [[ -n "${4:-}" ]]; then
    MODEL="$3"
    PROMPT="$4"
else
    MODEL="default"
    PROMPT="${3:-}"
fi

WORKSPACE_ROOT="/home/admin/openclaw/workspace"

# 允许显式传 REPO_ROOT；否则优先使用当前工作目录所在 git 仓库；再回退到 workspace。
if [[ -n "${REPO_ROOT:-}" ]]; then
    REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
elif git -C "$PWD" rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel)"
else
    REPO_ROOT="$WORKSPACE_ROOT"
fi

# 自动检测基础分支（优先当前分支，其次 master/main）
if [[ -z "${BASE_BRANCH:-}" ]]; then
    cd "$REPO_ROOT"
    BASE_BRANCH="$(git branch --show-current 2>/dev/null || true)"
    if [[ -z "$BASE_BRANCH" ]]; then
        if git show-ref --verify --quiet refs/heads/master; then
            BASE_BRANCH="master"
        elif git show-ref --verify --quiet refs/heads/main; then
            BASE_BRANCH="main"
        else
            BASE_BRANCH="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
        fi
    fi
fi

WORKTREE_ROOT="${WORKTREE_ROOT:-/home/admin/openclaw/agent-worktrees}"
TASK_REGISTRY="${TASK_REGISTRY:-$WORKSPACE_ROOT/.clawdbot/active-tasks.json}"
PROMPT_DIR="$WORKTREE_ROOT/.prompts"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 参数检查
if [[ -z "$TASK_ID" || -z "$AGENT_TYPE" || -z "$PROMPT" ]]; then
    log_error "用法: $0 <task-id> <agent-type> [model] <prompt>"
    echo "Agent 类型: codex | opencode | gemini | claude"
    exit 1
fi

if [[ ! -d "$REPO_ROOT/.git" && ! -f "$REPO_ROOT/.git" ]]; then
    log_error "REPO_ROOT 不是 git 仓库: $REPO_ROOT"
    exit 1
fi

if [[ -z "${BASE_BRANCH:-}" ]]; then
    log_error "无法自动检测基础分支，请显式设置 BASE_BRANCH"
    exit 1
fi

# 创建目录
mkdir -p "$WORKTREE_ROOT"
mkdir -p "$(dirname "$TASK_REGISTRY")"
mkdir -p "$PROMPT_DIR"

# 创建 worktree
WORKTREE_PATH="$WORKTREE_ROOT/$TASK_ID"
BRANCH_NAME="agent/$TASK_ID"
PROMPT_FILE="$PROMPT_DIR/$TASK_ID.txt"
RUNNER_FILE="$WORKTREE_PATH/.agent-runner.sh"

if [[ -d "$WORKTREE_PATH" ]]; then
    log_warn "Worktree 已存在: $WORKTREE_PATH"
else
    log_info "创建 worktree: $WORKTREE_PATH (repo: $REPO_ROOT, base: $BASE_BRANCH)"
    cd "$REPO_ROOT"
    git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$BASE_BRANCH" 2>/dev/null || {
        # 分支可能已存在
        git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    }
fi

# 保存 prompt 到文件，避免多行/代码块/引号被 shell 误解析
cat > "$PROMPT_FILE" <<EOF
$PROMPT
EOF

# 安装依赖（如果存在 package.json）
cd "$WORKTREE_PATH"
if [[ -f "package.json" ]]; then
    log_info "安装依赖..."
    pnpm install --frozen-lockfile 2>/dev/null || npm install --quiet
fi

# 创建 tmux session
TMUX_SESSION="agent-$TASK_ID"

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log_warn "Tmux session 已存在: $TMUX_SESSION"
else
    log_info "创建 tmux session: $TMUX_SESSION"
    tmux new-session -d -s "$TMUX_SESSION" -c "$WORKTREE_PATH"
fi

# 生成 runner 脚本，由 runner 在 session 内读取 prompt 文件并执行 agent
WORKTREE_PATH_Q=$(printf '%q' "$WORKTREE_PATH")
PROMPT_FILE_Q=$(printf '%q' "$PROMPT_FILE")
MODEL_Q=$(printf '%q' "$MODEL")
AGENT_TYPE_Q=$(printf '%q' "$AGENT_TYPE")
DEFAULT_SANDBOX_Q=$(printf '%q' "${SANDBOX:-workspace-write}")

cat > "$RUNNER_FILE" <<EOF
#!/bin/bash
set -euo pipefail
cd $WORKTREE_PATH_Q
PROMPT_FILE=$PROMPT_FILE_Q
PROMPT_CONTENT="
EOF
printf '$(cat -- %q)\n' "$PROMPT_FILE" >> "$RUNNER_FILE"
printf '"\n\ncase %s in\n' "$AGENT_TYPE_Q" >> "$RUNNER_FILE"
printf '    codex)\n' >> "$RUNNER_FILE"
printf '        SANDBOX="${SANDBOX:-%s}"\n' "$DEFAULT_SANDBOX_Q" >> "$RUNNER_FILE"
printf '        exec codex exec --skip-git-repo-check --sandbox "$SANDBOX" --full-auto "$PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    opencode)\n' >> "$RUNNER_FILE"
printf '        if [[ %s == default ]]; then\n' "$MODEL_Q" >> "$RUNNER_FILE"
printf '            exec opencode run "$PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        else\n' >> "$RUNNER_FILE"
printf '            exec opencode run --model %s "$PROMPT_CONTENT"\n' "$MODEL_Q" >> "$RUNNER_FILE"
printf '        fi\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    gemini|gemini-cli)\n' >> "$RUNNER_FILE"
printf '        exec gemini --yolo "$PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    claude|claude-code)\n' >> "$RUNNER_FILE"
printf '        MODEL_VALUE=%s\n' "$MODEL_Q" >> "$RUNNER_FILE"
printf '        if [[ "$MODEL_VALUE" == default ]]; then\n' >> "$RUNNER_FILE"
printf '            MODEL_VALUE=claude-sonnet-4\n' >> "$RUNNER_FILE"
printf '        fi\n' >> "$RUNNER_FILE"
printf '        exec claude --model "$MODEL_VALUE" --dangerously-skip-permissions -p "$PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    code-reviewer)\n' >> "$RUNNER_FILE"
printf '        exec gemini "使用 code-reviewer skill: $PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    docs-writer)\n' >> "$RUNNER_FILE"
printf '        exec gemini "使用 docs-writer skill: $PROMPT_CONTENT"\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf '    *)\n' >> "$RUNNER_FILE"
printf '        echo %q >&2\n' "未知 Agent 类型: $AGENT_TYPE" >> "$RUNNER_FILE"
printf '        exit 1\n' >> "$RUNNER_FILE"
printf '        ;;\n' >> "$RUNNER_FILE"
printf 'esac\n' >> "$RUNNER_FILE"
chmod +x "$RUNNER_FILE"

# 根据 Agent 类型启动
log_info "启动 $AGENT_TYPE agent..."
tmux send-keys -t "$TMUX_SESSION" "bash $RUNNER_FILE" Enter

# 注册任务
log_info "注册任务到 $TASK_REGISTRY"
mkdir -p "$(dirname "$TASK_REGISTRY")"

# 创建或更新任务注册表
if [[ ! -f "$TASK_REGISTRY" ]]; then
    echo '{"tasks": {}}' > "$TASK_REGISTRY"
fi

# 使用 jq 添加任务（如果可用）
if command -v jq &> /dev/null; then
    tmp_file=$(mktemp)
    jq --arg id "$TASK_ID" \
       --arg session "$TMUX_SESSION" \
       --arg agent "$AGENT_TYPE" \
       --arg prompt "$PROMPT" \
       --arg branch "$BRANCH_NAME" \
       --arg worktree "$WORKTREE_PATH" \
       --arg repo "$REPO_ROOT" \
       --arg base "$BASE_BRANCH" \
       --arg promptFile "$PROMPT_FILE" \
       '.tasks[$id] = {
           "tmuxSession": $session,
           "agent": $agent,
           "prompt": $prompt,
           "branch": $branch,
           "worktree": $worktree,
           "repoRoot": $repo,
           "baseBranch": $base,
           "promptFile": $promptFile,
           "status": "running",
           "createdAt": (now | todate),
           "notifyOnComplete": true,
           "attempts": 1
       }' "$TASK_REGISTRY" > "$tmp_file" && mv "$tmp_file" "$TASK_REGISTRY"
else
    log_warn "jq 未安装，跳过 JSON 注册"
fi

log_info "✅ Agent 已启动!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Task ID:     $TASK_ID"
echo "Agent:       $AGENT_TYPE"
echo "Model:       $MODEL"
echo "Repo root:   $REPO_ROOT"
echo "Base branch: $BASE_BRANCH"
echo "Worktree:    $WORKTREE_PATH"
echo "Branch:      $BRANCH_NAME"
echo "Prompt file: $PROMPT_FILE"
echo "Tmux:        tmux attach -t $TMUX_SESSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
