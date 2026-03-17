#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Codex CLI wrapper with cross-platform support, session management, and output saving.

Usage:
    New session:  uv run codex.py "task" [model] [workdir]
    Resume:       uv run codex.py resume <session_id> "task" [model] [workdir]
    Alternative:  python3 codex.py "task"
    Direct exec:  ./codex.py "task"

Environment Variables:
    CODEX_TIMEOUT: Override timeout (milliseconds or seconds)
"""

import subprocess
import json
import sys
import os
import time
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_WORKDIR = "."
DEFAULT_TIMEOUT = 7200  # 2 hours in seconds
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"


def get_script_base_dir() -> Path:
    """获取脚本所在目录的基础路径（项目根目录）"""
    # 脚本位于 .claude/skills/codex/scripts/codex.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def generate_output_filename(task: str) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_codex_<任务描述>.md"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 清理任务描述，只保留中文、英文、数字，截取前20个字符
    clean_task = "".join(c for c in task if c.isalnum() or "\u4e00" <= c <= "\u9fff")
    clean_task = clean_task[:20] if len(clean_task) > 20 else clean_task
    if not clean_task:
        clean_task = "task"

    return f"out_{date_str}_{time_str}_codex_{clean_task}.md"


def save_output_to_file(
    task: str,
    output: str,
    session_id: Optional[str] = None,
) -> Optional[str]:
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
            "# Codex CLI Output",
            "",
            f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Agent**: codex (CLI)\n**Model**: {DEFAULT_MODEL}",
            f"**任务**: {task}",
        ]

        if session_id:
            content_lines.append(f"**Session ID**: {session_id}")

        content_lines.extend(
            [
                "",
                "---",
                "",
                "## 输出内容",
                "",
                output,
            ]
        )

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


def resolve_timeout() -> int:
    """解析超时配置（秒）"""
    raw = os.environ.get("CODEX_TIMEOUT", "")
    if not raw:
        return DEFAULT_TIMEOUT

    try:
        parsed = int(raw)
        if parsed <= 0:
            log_warn(
                f"Invalid CODEX_TIMEOUT '{raw}', falling back to {DEFAULT_TIMEOUT}s"
            )
            return DEFAULT_TIMEOUT
        # 环境变量是毫秒，转换为秒
        return parsed // 1000 if parsed > 10000 else parsed
    except ValueError:
        log_warn(f"Invalid CODEX_TIMEOUT '{raw}', falling back to {DEFAULT_TIMEOUT}s")
        return DEFAULT_TIMEOUT


def normalize_text(text) -> Optional[str]:
    """规范化文本：字符串或字符串数组"""
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        return "".join(text)
    return None


def parse_args():
    """解析命令行参数"""
    if len(sys.argv) < 2:
        log_error("Task required")
        sys.exit(1)

    # 检测是否为 resume 模式
    if sys.argv[1] == "resume":
        if len(sys.argv) < 4:
            log_error("Resume mode requires: resume <session_id> <task>")
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


def build_codex_args(params: dict) -> list:
    """构建 codex CLI 参数"""
    if params["mode"] == "resume":
        return [
            "codex",
            "e",
            "--skip-git-repo-check",
            "--json",
            "resume",
            params["session_id"],
            params["task"],
        ]
    else:
        return [
            "codex",
            "e",
            "-m",
            params["model"],
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            params["workdir"],
            "--json",
            params["task"],
        ]


def run_codex_cli(
    params: dict, timeout_sec: int
) -> Tuple[int, str, str, Optional[str], Optional[str]]:
    """运行 Codex CLI，返回 (returncode, stdout, stderr, thread_id, agent_message)"""
    codex_args = build_codex_args(params)
    thread_id: Optional[str] = None
    last_agent_message: Optional[str] = None
    stderr_output = ""

    try:
        log_info(f"Starting Codex CLI with model {params.get('model', DEFAULT_MODEL)}")

        # 启动 codex 子进程
        process = subprocess.Popen(
            codex_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
        )

        # 逐行解析 JSON 输出
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)

                # 捕获 thread_id
                if event.get("type") == "thread.started":
                    thread_id = event.get("thread_id")

                # 捕获 agent_message
                if (
                    event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") == "agent_message"
                ):
                    text = normalize_text(event["item"].get("text"))
                    if text:
                        last_agent_message = text

            except json.JSONDecodeError:
                log_warn(f"Failed to parse line: {line}")

        # 等待进程结束
        returncode = process.wait(timeout=timeout_sec)
        stderr_output = process.stderr.read()

        return returncode, "", stderr_output, thread_id, last_agent_message

    except subprocess.TimeoutExpired:
        log_error("Codex execution timeout")
        process.kill()
        try:
            process.wait(timeout=FORCE_KILL_DELAY)
        except subprocess.TimeoutExpired:
            pass
        return 124, "", "Execution timeout", None, None

    except FileNotFoundError:
        log_error("codex command not found in PATH")
        return 127, "", "codex command not found", None, None


def main():
    log_info("Script started")
    params = parse_args()
    timeout_sec = resolve_timeout()
    log_info(f"Task: {params['task'][:50]}...")
    log_info(f"Timeout: {timeout_sec}s")

    # 如果指定了工作目录，切换到该目录
    workdir = params.get("workdir", DEFAULT_WORKDIR)
    if workdir != DEFAULT_WORKDIR:
        try:
            os.chdir(workdir)
        except FileNotFoundError:
            log_error(f"Working directory not found: {workdir}")
            sys.exit(1)
        except PermissionError:
            log_error(f"Permission denied: {workdir}")
            sys.exit(1)
        log_info("Changed working directory")

    returncode, stdout, stderr, thread_id, last_agent_message = run_codex_cli(
        params, timeout_sec
    )

    if stderr:
        sys.stderr.write(stderr)

    if returncode == 0:
        if last_agent_message:
            sys.stdout.write(f"{last_agent_message}\n")
            if thread_id:
                sys.stdout.write(f"\n---\nSESSION_ID: {thread_id}\n")
            saved_path = save_output_to_file(
                params["task"], last_agent_message, thread_id
            )
            if saved_path:
                log_info(f"Output saved to {saved_path}")
            sys.exit(0)
        else:
            log_error("Codex CLI completed without output")
            sys.exit(1)
    else:
        log_error(f"Codex CLI failed with code {returncode}")
        sys.exit(returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
