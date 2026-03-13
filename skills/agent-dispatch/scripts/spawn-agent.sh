#!/bin/bash
# spawn-agent.sh - 创建独立 worktree + tmux session 并启动 Agent
# 用法: ./spawn-agent.sh <task-id> <agent-type> [model] <prompt>
# 示例: ./spawn-agent.sh feat-templates codex "实现模板系统"
# 示例: ./spawn-agent.sh feat-templates codex gpt-5-codex "实现模板系统"

set -e

TASK_ID="$1"
AGENT_TYPE="$2"

# 判断第3个参数是 model 还是 prompt
# 如果有第4个参数，则第3个是 model，第4个是 prompt
# 否则第3个是 prompt，model 使用默认值
if [[ -n "$4" ]]; then
    MODEL="$3"
    PROMPT="$4"
else
    MODEL="default"
    PROMPT="$3"
fi

# Always use workspace as REPO_ROOT (don't rely on git detection)
REPO_ROOT="${REPO_ROOT:-/home/admin/openclaw/workspace}"

# 自动检测基础分支（优先 master，其次 main）
if [[ -z "$BASE_BRANCH" ]]; then
    cd "$REPO_ROOT"
    if git show-ref --verify --quiet refs/heads/master; then
        BASE_BRANCH="master"
    elif git show-ref --verify --quiet refs/heads/main; then
        BASE_BRANCH="main"
    else
        BASE_BRANCH="master"  # 默认回退
    fi
fi

WORKTREE_ROOT="${WORKTREE_ROOT:-/home/admin/openclaw/agent-worktrees}"
TASK_REGISTRY="$REPO_ROOT/.clawdbot/active-tasks.json"

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

# 创建目录
mkdir -p "$WORKTREE_ROOT"
mkdir -p "$(dirname "$TASK_REGISTRY")"

# 创建 worktree
WORKTREE_PATH="$WORKTREE_ROOT/$TASK_ID"
BRANCH_NAME="agent/$TASK_ID"

if [[ -d "$WORKTREE_PATH" ]]; then
    log_warn "Worktree 已存在: $WORKTREE_PATH"
else
    log_info "创建 worktree: $WORKTREE_PATH"
    cd "$REPO_ROOT"
    git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$BASE_BRANCH" 2>/dev/null || {
        # 分支可能已存在
        git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    }
fi

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

# 根据 Agent 类型启动
log_info "启动 $AGENT_TYPE agent..."
case "$AGENT_TYPE" in
    codex)
        # Codex 使用 codex exec 命令
        # 使用默认模型（gpt-5.4），不手动指定
        # 默认使用 workspace-write 模式（允许修改文件）
        SANDBOX="${SANDBOX:-workspace-write}"
        # 使用 --full-auto 即可，已包含自动批准
        # 注意：不使用 2>/dev/null，保留输出以便调试
        tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && codex exec --skip-git-repo-check --sandbox $SANDBOX --full-auto \"$PROMPT\"" Enter
        ;;
    opencode)
        # OpenCode 是核心工具，可处理所有类型任务
        # 不指定模型，使用 OpenCode 默认配置
        if [[ "$MODEL" == "default" ]]; then
            # 使用默认配置，不传 --model 参数
            tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && opencode run \"$PROMPT\"" Enter
        else
            # 用户指定了模型，使用指定的模型
            tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && opencode run --model $MODEL \"$PROMPT\"" Enter
        fi
        ;;
    gemini|gemini-cli)
        # Gemini CLI - 适合文档、写作、润色等文字类任务
        # Skills: code-reviewer, docs-writer
        # 使用 --yolo 模式自动批准所有操作
        tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && gemini --yolo \"$PROMPT\"" Enter
        ;;
    claude|claude-code)
        # Claude Code - 适合前端工作，速度快
        if [[ "$MODEL" == "default" ]]; then
            MODEL="claude-sonnet-4"
        fi
        tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && claude --model $MODEL --dangerously-skip-permissions -p \"$PROMPT\"" Enter
        ;;
    code-reviewer)
        # 使用 Gemini CLI 的 code-reviewer skill
        tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && gemini \"使用 code-reviewer skill: $PROMPT\"" Enter
        ;;
    docs-writer)
        # 使用 Gemini CLI 的 docs-writer skill
        tmux send-keys -t "$TMUX_SESSION" "cd $WORKTREE_PATH && gemini \"使用 docs-writer skill: $PROMPT\"" Enter
        ;;
    *)
        log_error "未知 Agent 类型: $AGENT_TYPE"
        echo "支持的 Agent 类型: codex | opencode | gemini | claude | code-reviewer | docs-writer"
        exit 1
        ;;
esac

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
       '.tasks[$id] = {
           "tmuxSession": $session,
           "agent": $agent,
           "prompt": $prompt,
           "branch": $branch,
           "worktree": $worktree,
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
echo "Worktree:    $WORKTREE_PATH"
echo "Branch:      $BRANCH_NAME"
echo "Tmux:        tmux attach -t $TMUX_SESSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
