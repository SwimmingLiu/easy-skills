#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Gemini CLI wrapper with cross-platform support.

Usage:
    uv run gemini.py "<prompt>" [workdir]
    python3 gemini.py "<prompt>"
    ./gemini.py "your prompt"

Environment Variables:
    GEMINI_MODEL: Configure model (default: gemini-3-pro-preview)
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")
DEFAULT_WORKDIR = "."
TIMEOUT_MS = 7_200_000  # 固定 2 小时，毫秒
DEFAULT_TIMEOUT = TIMEOUT_MS // 1000
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"


def get_script_base_dir() -> Path:
    """获取脚本所在目录的基础路径（项目根目录）"""
    # 脚本位于 .claude/skills/gemini/scripts/gemini.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def generate_output_filename(prompt: str) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_gemini_<任务描述>.md"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 清理任务描述，只保留中文、英文、数字，截取前20个字符
    clean_prompt = "".join(
        c for c in prompt if c.isalnum() or "\u4e00" <= c <= "\u9fff"
    )
    clean_prompt = clean_prompt[:20] if len(clean_prompt) > 20 else clean_prompt
    if not clean_prompt:
        clean_prompt = "task"

    return f"out_{date_str}_{time_str}_gemini_{clean_prompt}.md"


def save_output_to_file(prompt: str, output: str) -> Optional[str]:
    """将输出保存到 markdown 文件"""
    try:
        base_dir = get_script_base_dir()
        output_dir = base_dir / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = generate_output_filename(prompt)
        filepath = output_dir / filename

        # 构建 markdown 内容
        now = datetime.now()
        content_lines = [
            f"# Gemini Output",
            f"",
            f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Agent**: gemini",
            f"**Model**: {DEFAULT_MODEL}",
            f"**Prompt**: {prompt}",
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
        log_error("Prompt required")
        sys.exit(1)

    return {
        "prompt": sys.argv[1],
        "workdir": sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WORKDIR,
    }


def build_gemini_args(args) -> list:
    """构建 gemini CLI 参数"""
    # return ["gemini", "-m", DEFAULT_MODEL, "-p", args["prompt"]]
    # 暂时先不指定模型，使用默认模型
    return ["gemini", "-p", args["prompt"]]


def run_gemini(args) -> Tuple[int, str, str]:
    """运行 Gemini CLI，返回 (returncode, stdout, stderr)"""
    gemini_args = build_gemini_args(args)
    timeout_sec = DEFAULT_TIMEOUT

    try:
        log_info(f"Starting gemini with model {DEFAULT_MODEL}")
        process = subprocess.Popen(
            gemini_args,
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
        log_error(f"Gemini execution timeout ({timeout_sec}s)")
        process.kill()
        try:
            process.wait(timeout=FORCE_KILL_DELAY)
        except subprocess.TimeoutExpired:
            pass
        return 124, "", "Execution timeout"

    except FileNotFoundError:
        log_error("gemini command not found in PATH")
        return 127, "", "gemini command not found"


def main():
    log_info("Script started")
    args = parse_args()
    log_info(f"Prompt length: {len(args['prompt'])}")
    log_info(f"Working dir: {args['workdir']}")

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

    # 运行 Gemini CLI
    returncode, stdout, stderr = run_gemini(args)

    # 输出 stderr
    if stderr:
        sys.stderr.write(stderr)

    if returncode != 0:
        log_error(f"Gemini exited with status {returncode}")
        sys.exit(returncode)

    # Gemini CLI 成功
    if stdout.strip():
        saved_path = save_output_to_file(args["prompt"], stdout)
        if saved_path:
            log_info(f"Output saved to {saved_path}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
