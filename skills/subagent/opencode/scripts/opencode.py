#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
OpenCode CLI wrapper with cross-platform support, session management, and output saving.

Usage:
    uv run opencode.py "<task>" [model] [workdir]
    uv run opencode.py resume <session_id> "<task>" [model] [workdir]
    python3 opencode.py "<task>"
    ./opencode.py "your task"

Environment Variables:
    OPENCODE_MODEL: Override model (default: uses CLI default model)
    OPENCODE_AGENT: Configure agent (default: none)
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_MODEL = os.environ.get("OPENCODE_MODEL", None)  # None means use CLI default
DEFAULT_WORKDIR = "."
TIMEOUT_MS = 7_200_000  # 固定 2 小时，毫秒
DEFAULT_TIMEOUT = TIMEOUT_MS // 1000
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"


def get_script_base_dir() -> Path:
    """获取脚本所在目录的基础路径（项目根目录）"""
    # 脚本位于 .claude/skills/opencode/scripts/opencode.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def generate_output_filename(task: str) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_opencode_<任务描述>.md"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 清理任务描述，只保留中文、英文、数字，截取前20个字符
    clean_task = "".join(
        c for c in task if c.isalnum() or "\u4e00" <= c <= "\u9fff"
    )
    clean_task = clean_task[:20] if len(clean_task) > 20 else clean_task
    if not clean_task:
        clean_task = "task"

    return f"out_{date_str}_{time_str}_opencode_{clean_task}.md"


def save_output_to_file(task: str, output: str, session_id: Optional[str] = None, model: str = DEFAULT_MODEL) -> Optional[str]:
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
            f"# OpenCode Output",
            f"",
            f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Model**: {model}",
        ]

        if session_id:
            content_lines.append(f"**Session ID**: {session_id}")

        content_lines.extend([
            f"**Task**: {task}",
            f"",
            f"---",
            f"",
            f"## 输出内容",
            f"",
            output,
        ])

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

    # 检查是否是 resume 模式
    if sys.argv[1] == "resume":
        if len(sys.argv) < 4:
            log_error("Resume mode requires: resume <session_id> <task> [model] [workdir]")
            sys.exit(1)
        return {
            "mode": "resume",
            "session_id": sys.argv[2],
            "task": sys.argv[3],
            "model": sys.argv[4] if len(sys.argv) > 4 else DEFAULT_MODEL,
            "workdir": sys.argv[5] if len(sys.argv) > 5 else DEFAULT_WORKDIR,
        }
    else:
        return {
            "mode": "new",
            "task": sys.argv[1],
            "model": sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL,
            "workdir": sys.argv[3] if len(sys.argv) > 3 else DEFAULT_WORKDIR,
        }


def build_opencode_args(args) -> list:
    """构建 OpenCode CLI 参数"""
    cmd_args = ["opencode", "run"]

    # 不指定模型，使用 CLI 默认模型
    # 如果需要指定模型，请设置环境变量 OPENCODE_MODEL
    if os.environ.get("OPENCODE_MODEL"):
        cmd_args.extend(["--model", os.environ.get("OPENCODE_MODEL")])

    # 添加 agent 参数（如果设置了环境变量）
    agent = os.environ.get("OPENCODE_AGENT")
    if agent:
        cmd_args.extend(["--agent", agent])

    # 添加 resume 或 session 参数
    if args["mode"] == "resume":
        cmd_args.extend(["--session", args["session_id"]])

    # 添加任务描述
    cmd_args.append(args["task"])

    return cmd_args


def extract_session_id(output: str) -> Optional[str]:
    """从输出中提取 session ID"""
    # OpenCode 通常在最后输出 session ID
    # 格式可能是: SESSION_ID: xxx 或 session: xxx
    lines = output.strip().split("\n")
    for line in reversed(lines):
        if "SESSION_ID:" in line or "session:" in line.lower():
            # 提取 session ID
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    return None


def run_opencode(args) -> Tuple[int, str, str]:
    """运行 OpenCode CLI，返回 (returncode, stdout, stderr)"""
    opencode_args = build_opencode_args(args)
    timeout_sec = DEFAULT_TIMEOUT

    try:
        log_info(f"Starting OpenCode with model {args['model']}")
        process = subprocess.Popen(
            opencode_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        output_lines = []
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output_lines.append(line)

        returncode = process.wait(timeout=timeout_sec)
        stderr_output = process.stderr.read()

        return returncode, "".join(output_lines), stderr_output

    except subprocess.TimeoutExpired:
        log_error(f"OpenCode execution timeout ({timeout_sec}s)")
        process.kill()
        try:
            process.wait(timeout=FORCE_KILL_DELAY)
        except subprocess.TimeoutExpired:
            pass
        return 124, "", "Execution timeout"

    except FileNotFoundError:
        log_error("opencode command not found in PATH")
        return 127, "", "opencode command not found"


def main():
    log_info("Script started")
    args = parse_args()

    if args["mode"] == "resume":
        log_info(f"Mode: resume session {args['session_id']}")

    log_info(f"Task: {args['task'][:50]}...")
    log_info(f"Timeout: {DEFAULT_TIMEOUT}s")
    log_info(f"Working dir: {args['workdir']}")

    # 如果指定了工作目录，切换到该目录
    if args["workdir"] != DEFAULT_WORKDIR:
        try:
            os.chdir(args["workdir"])
            log_info("Changed working directory")
        except FileNotFoundError:
            log_error(f"Working directory not found: {args['workdir']}")
            sys.exit(1)
        except PermissionError:
            log_error(f"Permission denied: {args['workdir']}")
            sys.exit(1)

    # 运行 OpenCode CLI
    returncode, stdout, stderr = run_opencode(args)

    # 输出 stderr
    if stderr:
        sys.stderr.write(stderr)

    if returncode != 0:
        log_error(f"OpenCode exited with status {returncode}")
        sys.exit(returncode)

    # OpenCode CLI 成功
    if stdout.strip():
        # 提取 session ID
        session_id = extract_session_id(stdout)

        # 保存输出
        saved_path = save_output_to_file(args["task"], stdout, session_id, args["model"])
        if saved_path:
            log_info(f"Output saved to {saved_path}")

        # 输出 session ID（如果没有在原始输出中）
        if session_id and "SESSION_ID:" not in stdout:
            sys.stdout.write(f"\n---\nSESSION_ID: {session_id}\n")
            sys.stdout.flush()

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
