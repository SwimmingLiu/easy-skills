#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Codex Fallback Script - 使用 OpenCode review agent 模式调用 Tuzi API gpt-5.1-codex

当 Codex CLI 不可用时（账户限制、额度用尽等），作为降级方案执行。

调用方式:
    opencode run --agent review --model "tuzi/gpt-5.1-codex" "<task>"

Usage:
    New session:  uv run codex_fallback.py "task" [workdir]
    python3 codex_fallback.py "task"
    ./codex_fallback.py "task"
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import certifi
except Exception:  # pragma: no cover - optional dependency
    certifi = None

# OpenCode 配置
OPENCODE_AGENT = "review"
OPENCODE_MODEL = "tuzi/gpt-5.1-codex"
DEFAULT_WORKDIR = "."
DEFAULT_TIMEOUT = 7200  # 2 hours in seconds
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"


def get_script_base_dir() -> Path:
    """获取脚本所在目录的基础路径（项目根目录）"""
    # 脚本位于 .claude/skills/codex/scripts/codex_fallback.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def generate_output_filename(task: str) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_codex_fallback_<任务描述>.md"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 清理任务描述，只保留中文、英文、数字，截取前20个字符
    clean_task = "".join(c for c in task if c.isalnum() or "\u4e00" <= c <= "\u9fff")
    clean_task = clean_task[:20] if len(clean_task) > 20 else clean_task
    if not clean_task:
        clean_task = "task"

    return f"out_{date_str}_{time_str}_codex_fallback_{clean_task}.md"


def save_output_to_file(task: str, output: str) -> Optional[str]:
    """将输出保存到 markdown 文件"""
    try:
        base_dir = get_script_base_dir()
        output_dir = base_dir / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = generate_output_filename(task)
        filepath = output_dir / filename

        # 构建 markdown 内容
        now = datetime.now()
        content_lines = [
            f"# Codex Fallback Output",
            f"",
            f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Agent**: OpenCode {OPENCODE_AGENT}",
            f"**Model**: {OPENCODE_MODEL}",
            f"**任务**: {task}",
            f"**模式**: 降级模式 (Codex CLI 不可用)",
            f'**调用命令**: `opencode run --agent {OPENCODE_AGENT} --model "{OPENCODE_MODEL}" "<task>"`',
            f"",
            f"---",
            f"",
            f"## 输出内容",
            f"",
            output,
        ]

        content = "\n".join(content_lines)
        filepath.write_text(content, encoding="utf-8")

        return str(filepath)
    except Exception as e:
        log_warn(f"Failed to save output to file: {e}")
        return None


def log_error(message: str):
    """输出错误信息到 stderr"""
    sys.stderr.write(f"ERROR: {message}\n")


def log_warn(message: str):
    """输出警告信息到 stderr"""
    sys.stderr.write(f"WARN: {message}\n")


def log_info(message: str):
    """输出信息到 stderr"""
    sys.stderr.write(f"INFO: {message}\n")


def parse_args():
    """解析位置参数"""
    if len(sys.argv) < 2:
        log_error("Task required")
        sys.exit(1)

    return {
        "task": sys.argv[1],
        "workdir": sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WORKDIR,
    }


def build_opencode_args(args) -> list:
    """构建 OpenCode CLI 参数"""
    return [
        "opencode",
        "run",
        "--agent",
        OPENCODE_AGENT,
        "--model",
        OPENCODE_MODEL,
        args["task"],
    ]


def build_opencode_env() -> dict:
    """构建 OpenCode 子进程环境，移除桌面客户端变量"""
    env = os.environ.copy()
    for key in (
        "OPENCODE",
        "OPENCODE_CLIENT",
        "OPENCODE_SERVER_USERNAME",
        "OPENCODE_SERVER_PASSWORD",
        "OPENCODE_SERVER_URL",
        "XDG_STATE_HOME",
    ):
        env.pop(key, None)
    if certifi is not None:
        env.setdefault("NODE_EXTRA_CA_CERTS", certifi.where())
    env.setdefault("OPENCODE_CLIENT", "cli")
    return env


def main():
    log_info("Codex Fallback Script started")
    log_info(f"Using OpenCode agent: {OPENCODE_AGENT}, model: {OPENCODE_MODEL}")
    log_info(
        f'Command: opencode run --agent {OPENCODE_AGENT} --model "{OPENCODE_MODEL}" "<task>"'
    )

    args = parse_args()
    log_info(f"Task length: {len(args['task'])}")
    log_info(f"Working dir: {args['workdir']}")

    opencode_args = build_opencode_args(args)
    timeout_sec = DEFAULT_TIMEOUT
    log_info(f"Timeout: {timeout_sec}s")

    # 如果指定了工作目录，切换到该目录
    if args["workdir"] != DEFAULT_WORKDIR:
        try:
            os.chdir(args["workdir"])
        except FileNotFoundError:
            log_error(f"Working directory not found: {args['workdir']}")
            sys.exit(1)
        except PermissionError:
            log_error(f"Permission denied: {args['workdir']}")
            sys.exit(1)
        log_info("Changed working directory")

    try:
        log_info(
            f"Starting OpenCode with agent={OPENCODE_AGENT}, model={OPENCODE_MODEL}"
        )
        process = None
        output_lines = []  # 收集输出用于保存到文件

        # 启动 OpenCode 子进程
        process = subprocess.Popen(
            opencode_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            env=build_opencode_env(),
        )

        # 实时输出 stdout，同时收集输出
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output_lines.append(line)

        # 等待进程结束
        returncode = process.wait(timeout=timeout_sec)

        # 读取 stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            sys.stderr.write(stderr_output)

        # 检查退出码
        if returncode != 0:
            log_error(f"OpenCode exited with status {returncode}")
            sys.exit(returncode)

        # 保存输出到 markdown 文件
        full_output = "".join(output_lines)
        if full_output.strip():
            saved_path = save_output_to_file(args["task"], full_output)
            if saved_path:
                log_info(f"Output saved to {saved_path}")

        sys.exit(0)

    except subprocess.TimeoutExpired:
        log_error(f"OpenCode execution timeout ({timeout_sec}s)")
        if process is not None:
            process.kill()
            try:
                process.wait(timeout=FORCE_KILL_DELAY)
            except subprocess.TimeoutExpired:
                pass
        sys.exit(124)

    except FileNotFoundError:
        log_error("opencode command not found in PATH")
        log_error("Please install OpenCode: https://opencode.ai")
        sys.exit(127)

    except KeyboardInterrupt:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=FORCE_KILL_DELAY)
            except subprocess.TimeoutExpired:
                process.kill()
        sys.exit(130)


if __name__ == "__main__":
    main()
