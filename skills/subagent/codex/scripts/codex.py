#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Codex CLI wrapper with cross-platform support, session management, and automatic fallback.

当 Codex CLI 不可用时（账户限制、额度用尽、认证失败等），
自动降级到 OpenCode review agent 模式，使用 Tuzi API 的 gpt-5.1-codex 模型。

Usage:
    New session:  uv run codex.py "task" [model] [workdir]
    Resume:       uv run codex.py resume <session_id> "task" [model] [workdir]
    Alternative:  python3 codex.py "task"
    Direct exec:  ./codex.py "task"

Environment Variables:
    CODEX_TIMEOUT: Override timeout (milliseconds or seconds)
    CODEX_FORCE_FALLBACK: Set to "1" to force fallback mode (for testing)
"""

import subprocess
import json
import sys
import os
import re
import socket
import time
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_WORKDIR = "."
DEFAULT_TIMEOUT = 7200  # 2 hours in seconds
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"

ATTACH_HOST = "127.0.0.1"
ATTACH_PORT = 4096
SERVER_START_TIMEOUT = 5

# 降级配置
FALLBACK_AGENT = "review"
FALLBACK_MODEL = "tuzi/gpt-5.1-codex"
FALLBACK_MODEL_SECONDARY = os.environ.get(
    "CODEX_FALLBACK_MODEL_SECONDARY", "tuzi/gpt-5.1-codex"
)

# 需要触发降级的错误模式
FALLBACK_ERROR_PATTERNS = [
    r"rate\s*limit\s*exceeded",
    r"quota\s*exceeded",
    r"authentication\s*failed",
    r"401",
    r"403",
    r"account\s*suspended",
    r"account\s*restricted",
    r"billing",
    r"payment",
    r"api\s*key.*invalid",
    r"api\s*key.*expired",
    r"connection\s*timed?\s*out",
    r"network\s*error",
    r"service\s*unavailable",
    r"503",
    r"429",  # Too Many Requests
    r"insufficient\s*quota",
    r"resource\s*exhausted",
    r"permission\s*denied",
    r"access\s*denied",
    r"unauthorized",
    r"invalid\s*api\s*key",
    r"expired\s*token",
    r"token\s*expired",
]


def get_script_base_dir() -> Path:
    """获取脚本所在目录的基础路径（项目根目录）"""
    # 脚本位于 .claude/skills/codex/scripts/codex.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def generate_output_filename(task: str, is_fallback: bool = False) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_codex[_fallback]_<任务描述>.md"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 清理任务描述，只保留中文、英文、数字，截取前20个字符
    clean_task = "".join(c for c in task if c.isalnum() or "\u4e00" <= c <= "\u9fff")
    clean_task = clean_task[:20] if len(clean_task) > 20 else clean_task
    if not clean_task:
        clean_task = "task"

    suffix = "codex_fallback" if is_fallback else "codex"
    return f"out_{date_str}_{time_str}_{suffix}_{clean_task}.md"


def save_output_to_file(
    task: str,
    output: str,
    session_id: Optional[str] = None,
    source: str = "codex_cli",  # "codex_cli" or "opencode_agent"
) -> Optional[str]:
    """将输出保存到 markdown 文件"""
    try:
        base_dir = get_script_base_dir()
        output_dir = base_dir / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        is_agent = source == "opencode_agent"
        filename = generate_output_filename(task, is_agent)
        filepath = output_dir / filename

        # 构建 markdown 内容
        now = datetime.now()

        if source == "opencode_agent":
            header = "# OpenCode Agent Output"
            agent_info = (
                f"**Agent**: OpenCode {FALLBACK_AGENT}\n**Model**: {FALLBACK_MODEL}"
            )
            cmd_info = f'**调用命令**: `opencode run --agent {FALLBACK_AGENT} --model "{FALLBACK_MODEL}" "<task>"`'
        else:
            header = "# Codex CLI Output"
            agent_info = f"**Agent**: codex (CLI)\n**Model**: {DEFAULT_MODEL}"
            cmd_info = ""

        content_lines = [
            header,
            "",
            f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            agent_info,
            f"**任务**: {task}",
        ]

        if cmd_info:
            content_lines.append(cmd_info)

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


def build_fallback_args(params: dict) -> list:
    """构建 OpenCode 降级调用参数"""
    return [
        "opencode",
        "run",
        "--agent",
        FALLBACK_AGENT,
        "--model",
        FALLBACK_MODEL,
        params["task"],
    ]


def build_fallback_args_with_model(params: dict, model: str) -> list:
    return [
        "opencode",
        "run",
        "--agent",
        FALLBACK_AGENT,
        "--model",
        model,
        params["task"],
    ]


def build_fallback_args_with_attach(params: dict, attach_url: str, model: str) -> list:
    return [
        "opencode",
        "run",
        "--attach",
        attach_url,
        "--agent",
        FALLBACK_AGENT,
        "--model",
        model,
        params["task"],
    ]


def should_fallback(error_output: str, returncode: int) -> bool:
    """检测是否需要降级"""
    # 命令未找到也需要降级
    if returncode == 127:
        return True

    # 超时也需要降级
    if returncode == 124:
        return True

    # 检查错误输出是否匹配降级模式
    error_lower = error_output.lower()
    for pattern in FALLBACK_ERROR_PATTERNS:
        if re.search(pattern, error_lower, re.IGNORECASE):
            return True

    return False


def is_session_not_found(output_text: str) -> bool:
    return "session not found" in output_text.lower()


def is_model_not_found(output_text: str) -> bool:
    lowered = output_text.lower()
    return (
        "modelnotfound" in lowered
        or "providermodelnotfound" in lowered
        or "model not found" in lowered
        or "providermodelnotfounderror" in lowered
    )


def build_opencode_env() -> dict:
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
    env.setdefault("OPENCODE_CLIENT", "cli")
    return env


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ATTACH_HOST, 0))
        return sock.getsockname()[1]


def is_port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout_sec: int) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        if is_port_open(host, port):
            return True
        time.sleep(0.1)
    return False


def check_force_fallback() -> bool:
    """检查是否强制使用降级模式（用于测试）"""
    return os.environ.get("CODEX_FORCE_FALLBACK", "").lower() in ("1", "true", "yes")


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


def run_opencode_agent(params: dict, timeout_sec: int) -> Tuple[int, str, str]:
    """运行 OpenCode review agent，返回 (returncode, stdout, stderr)"""
    log_info(f"Starting OpenCode agent ({FALLBACK_AGENT}) with model {FALLBACK_MODEL}")
    log_info(
        f'Command: opencode run --agent {FALLBACK_AGENT} --model "{FALLBACK_MODEL}" "<task>"'
    )

    return run_opencode_with_retries(params, timeout_sec, FALLBACK_MODEL)


def run_opencode(
    params: dict, timeout_sec: int, model: str, attach_url: Optional[str] = None
) -> Tuple[int, str, str]:
    if attach_url:
        fallback_args = build_fallback_args_with_attach(params, attach_url, model)
    else:
        fallback_args = build_fallback_args_with_model(params, model)

    try:
        process = subprocess.Popen(
            fallback_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=build_opencode_env(),
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
        log_error(f"Fallback execution timeout ({timeout_sec}s)")
        process.kill()
        try:
            process.wait(timeout=FORCE_KILL_DELAY)
        except subprocess.TimeoutExpired:
            pass
        return 124, "", "Fallback execution timeout"

    except FileNotFoundError:
        log_error("opencode command not found in PATH")
        log_error("Please install OpenCode: https://opencode.ai")
        return 127, "", "opencode command not found"


def run_opencode_with_server(
    params: dict, timeout_sec: int, model: str
) -> Tuple[int, str, str]:
    port = get_free_port()
    attach_url = f"http://{ATTACH_HOST}:{port}"
    started_server = False
    server_process = None

    if not is_port_open(ATTACH_HOST, port):
        try:
            server_process = subprocess.Popen(
                [
                    "opencode",
                    "serve",
                    "--port",
                    str(port),
                    "--hostname",
                    ATTACH_HOST,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                env=build_opencode_env(),
            )
            started_server = True
        except FileNotFoundError:
            log_error("opencode command not found in PATH")
            log_error("Please install OpenCode: https://opencode.ai")
            return 127, "", "opencode command not found"

        if not wait_for_port(ATTACH_HOST, port, SERVER_START_TIMEOUT):
            if started_server and server_process:
                server_process.terminate()
            log_error("OpenCode server failed to start")
            return 1, "", "OpenCode server failed to start"

    log_info(f"Using OpenCode attach: {attach_url}")
    try:
        return run_opencode(params, timeout_sec, model=model, attach_url=attach_url)
    finally:
        if started_server and server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                server_process.kill()


def run_opencode_with_retries(
    params: dict, timeout_sec: int, model: str
) -> Tuple[int, str, str]:
    returncode, stdout, stderr = run_opencode(params, timeout_sec, model=model)
    combined = f"{stdout}\n{stderr}"
    if returncode != 0 and is_session_not_found(combined):
        log_warn("OpenCode session not found, retrying with local server")
        returncode, stdout, stderr = run_opencode_with_server(
            params, timeout_sec, model=model
        )
        combined = f"{stdout}\n{stderr}"

    if returncode != 0 and is_model_not_found(combined):
        if FALLBACK_MODEL_SECONDARY and FALLBACK_MODEL_SECONDARY != model:
            log_warn(
                f"OpenCode model not found: {model}. Retrying with {FALLBACK_MODEL_SECONDARY}"
            )
            return run_opencode_with_retries(
                params, timeout_sec, FALLBACK_MODEL_SECONDARY
            )

    return returncode, stdout, stderr


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

    # 检查是否强制使用 CLI 优先模式 (恢复旧行为)
    force_cli_first = os.environ.get("CODEX_USE_CLI_FIRST", "").lower() in (
        "1",
        "true",
        "yes",
    )

    # 检查是否强制使用 Agent 模式 (原 CODEX_FORCE_FALLBACK)
    force_agent = os.environ.get("CODEX_FORCE_FALLBACK", "").lower() in (
        "1",
        "true",
        "yes",
    )

    if force_agent:
        log_warn("CODEX_FORCE_FALLBACK set, forcing OpenCode Agent mode")
        # 强制 Agent 模式
        returncode, stdout, stderr = run_opencode_agent(params, timeout_sec)

        if stderr:
            sys.stderr.write(stderr)

        if returncode == 0 and stdout.strip():
            saved_path = save_output_to_file(
                params["task"], stdout, source="opencode_agent"
            )
            if saved_path:
                log_info(f"OpenCode Agent output saved to {saved_path}")
            sys.exit(0)
        else:
            log_error(f"OpenCode Agent failed with code {returncode}")
            sys.exit(returncode)

    # 决策执行顺序
    # Resume 模式必须优先使用 CLI (因为 Agent 暂不支持 resume)
    is_resume = params["mode"] == "resume"

    if is_resume or force_cli_first:
        # 策略 A: 优先 CLI -> 失败则尝试 Agent
        if is_resume:
            log_info("Resume mode detected: Prioritizing Codex CLI")
        elif force_cli_first:
            log_info("CODEX_USE_CLI_FIRST set: Prioritizing Codex CLI")

        # 1. 尝试 CLI
        returncode, stdout, stderr, thread_id, last_agent_message = run_codex_cli(
            params, timeout_sec
        )

        if stderr:
            sys.stderr.write(stderr)

        # 成功则直接退出
        if returncode == 0:
            if last_agent_message:
                sys.stdout.write(f"{last_agent_message}\n")
                if thread_id:
                    sys.stdout.write(f"\n---\nSESSION_ID: {thread_id}\n")
                saved_path = save_output_to_file(
                    params["task"], last_agent_message, thread_id, source="codex_cli"
                )
                if saved_path:
                    log_info(f"Output saved to {saved_path}")
                sys.exit(0)
            else:
                log_error("Codex CLI completed without output")
                sys.exit(1)

        # 2. CLI 失败，尝试 Agent (仅当不是 Resume 模式或明确允许时)
        # 注意: Resume 模式下切换到 Agent 会丢失上下文，但也许比完全失败好？
        # 目前保持旧行为: 如果 CLI 失败且符合降级条件，尝试 Agent
        if should_fallback(stderr, returncode):
            log_warn(
                f"Codex CLI failed (code {returncode}), switching to OpenCode Agent"
            )
            if is_resume:
                log_warn(
                    "WARNING: Resuming session is NOT supported in OpenCode Agent mode. Starting new session."
                )

            returncode, stdout, stderr = run_opencode_agent(params, timeout_sec)

            if stderr:
                sys.stderr.write(stderr)

            if returncode == 0 and stdout.strip():
                saved_path = save_output_to_file(
                    params["task"], stdout, source="opencode_agent"
                )
                if saved_path:
                    log_info(f"OpenCode Agent output saved to {saved_path}")
                sys.exit(0)
            else:
                log_error(f"OpenCode Agent also failed with code {returncode}")
                sys.exit(returncode)
        else:
            log_error(f"Codex CLI failed with status {returncode}")
            sys.exit(returncode)

    else:
        # 策略 B (默认): 优先 Agent -> 失败则尝试 CLI
        log_info("Default Strategy: Prioritizing OpenCode Agent")

        # 1. 尝试 Agent
        returncode, stdout, stderr = run_opencode_agent(params, timeout_sec)

        # 如果 Agent 成功，直接返回
        if returncode == 0:
            if stderr:
                sys.stderr.write(stderr)  # 打印可能的警告

            if stdout.strip():
                sys.stdout.write(stdout)  # 输出结果
                saved_path = save_output_to_file(
                    params["task"], stdout, source="opencode_agent"
                )
                if saved_path:
                    log_info(f"OpenCode Agent output saved to {saved_path}")
                sys.exit(0)
            else:
                log_warn("OpenCode Agent returned empty output, trying Codex CLI...")

        # 2. Agent 失败 (或输出为空)，尝试 CLI
        if returncode != 0:
            log_warn(
                f"OpenCode Agent failed (code {returncode}), switching to Codex CLI"
            )
            if stderr:
                sys.stderr.write(stderr)

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
                    params["task"], last_agent_message, thread_id, source="codex_cli"
                )
                if saved_path:
                    log_info(f"Output saved to {saved_path}")
                sys.exit(0)
            else:
                log_error("Codex CLI completed without output")
                sys.exit(1)
        else:
            log_error(f"Codex CLI also failed with code {returncode}")
            sys.exit(returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
