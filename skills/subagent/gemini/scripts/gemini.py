#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Gemini CLI wrapper with cross-platform support and automatic fallback.

当 Gemini CLI 不可用时（账户限制、额度用尽、认证失败等），
自动降级到 OpenCode paper agent 模式，使用 Tuzi API 的 gemini-3-pro 模型。

Usage:
    uv run gemini.py "<prompt>" [workdir]
    python3 gemini.py "<prompt>"
    ./gemini.py "your prompt"

Environment Variables:
    GEMINI_MODEL: Configure model (default: gemini-3-pro-preview)
    GEMINI_FORCE_FALLBACK: Set to "1" to force fallback mode (for testing)
"""

import subprocess
import sys
import os
import re
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")
DEFAULT_WORKDIR = "."
TIMEOUT_MS = 7_200_000  # 固定 2 小时，毫秒
DEFAULT_TIMEOUT = TIMEOUT_MS // 1000
FORCE_KILL_DELAY = 5
OUTPUT_DIR = ".tmp/docs/output"

ATTACH_HOST = "127.0.0.1"
ATTACH_PORT = 4096
SERVER_START_TIMEOUT = 5

# 降级配置
FALLBACK_AGENT = "paper"
FALLBACK_MODEL = "tuzi/gemini-3-flash-preview-all"
FALLBACK_MODEL_SECONDARY = os.environ.get(
    "GEMINI_FALLBACK_MODEL_SECONDARY", "tuzi/gemini-3-flash-preview-all"
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
    # 脚本位于 .claude/skills/gemini/scripts/gemini.py
    # 需要向上4级才能到达项目根目录
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent.parent.parent


def get_fallback_script_path() -> Path:
    """获取降级脚本路径"""
    return Path(__file__).resolve().parent / "gemini_fallback.py"


def generate_output_filename(prompt: str, is_fallback: bool = False) -> str:
    """生成输出文件名，格式: out_<日期>_<时间>_gemini[_fallback]_<任务描述>.md"""
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

    suffix = "gemini_fallback" if is_fallback else "gemini"
    return f"out_{date_str}_{time_str}_{suffix}_{clean_prompt}.md"


def save_output_to_file(
    prompt: str, output: str, is_fallback: bool = False
) -> Optional[str]:
    """将输出保存到 markdown 文件"""
    try:
        base_dir = get_script_base_dir()
        output_dir = base_dir / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = generate_output_filename(prompt, is_fallback)
        filepath = output_dir / filename

        # 构建 markdown 内容
        now = datetime.now()
        if is_fallback:
            content_lines = [
                f"# Gemini Fallback Output",
                f"",
                f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Agent**: OpenCode {FALLBACK_AGENT}",
                f"**Model**: {FALLBACK_MODEL}",
                f"**Prompt**: {prompt}",
                f"**模式**: 降级模式 (Gemini CLI 不可用)",
                f"",
                f"---",
                f"",
                f"## 输出内容",
                f"",
                output,
            ]
        else:
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


def build_fallback_args(args) -> list:
    """构建 OpenCode 降级调用参数"""
    return [
        "opencode",
        "run",
        "--agent",
        FALLBACK_AGENT,
        "--model",
        FALLBACK_MODEL,
        args["prompt"],
    ]


def build_fallback_args_with_model(args, model: str) -> list:
    return [
        "opencode",
        "run",
        "--agent",
        FALLBACK_AGENT,
        "--model",
        model,
        args["prompt"],
    ]


def build_fallback_args_with_attach(args, attach_url: str, model: str) -> list:
    return [
        "opencode",
        "run",
        "--attach",
        attach_url,
        "--agent",
        FALLBACK_AGENT,
        "--model",
        model,
        args["prompt"],
    ]


def should_fallback(error_output: str, returncode: int) -> bool:
    """检测是否需要降级"""
    # 命令未找到也需要降级
    if returncode == 127:
        return True

    # 超时也需要降级
    if returncode == 124:
        return True

    # 非零返回码且有错误输出，检查错误模式
    if returncode != 0:
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
    return os.environ.get("GEMINI_FORCE_FALLBACK", "").lower() in ("1", "true", "yes")


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


def run_fallback(args) -> Tuple[int, str, str]:
    """运行降级方案（OpenCode paper agent），返回 (returncode, stdout, stderr)"""
    log_warn("Gemini CLI unavailable, falling back to OpenCode paper agent")
    log_info(f"Using agent={FALLBACK_AGENT}, model={FALLBACK_MODEL}")
    log_info(
        f'Command: opencode run --agent {FALLBACK_AGENT} --model "{FALLBACK_MODEL}" "<prompt>"'
    )

    return run_opencode_with_retries(args, FALLBACK_MODEL)


def run_opencode(
    args, model: str, attach_url: Optional[str] = None
) -> Tuple[int, str, str]:
    if attach_url:
        fallback_args = build_fallback_args_with_attach(args, attach_url, model)
    else:
        fallback_args = build_fallback_args_with_model(args, model)

    timeout_sec = DEFAULT_TIMEOUT
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


def run_opencode_with_server(args, model: str) -> Tuple[int, str, str]:
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
        return run_opencode(args, model=model, attach_url=attach_url)
    finally:
        if started_server and server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                server_process.kill()


def run_opencode_with_retries(args, model: str) -> Tuple[int, str, str]:
    returncode, stdout, stderr = run_opencode(args, model=model)
    combined = f"{stdout}\n{stderr}"
    if is_session_not_found(combined):
        log_warn("OpenCode session not found, retrying with local server")
        returncode, stdout, stderr = run_opencode_with_server(args, model=model)
        combined = f"{stdout}\n{stderr}"

    if is_model_not_found(combined):
        if FALLBACK_MODEL_SECONDARY and FALLBACK_MODEL_SECONDARY != model:
            log_warn(
                f"OpenCode model not found: {model}. Retrying with {FALLBACK_MODEL_SECONDARY}"
            )
            return run_opencode_with_retries(args, FALLBACK_MODEL_SECONDARY)

    return returncode, stdout, stderr


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

    # 检查是否强制使用降级模式
    if check_force_fallback():
        log_warn("GEMINI_FORCE_FALLBACK is set, using fallback mode directly")
        returncode, stdout, stderr = run_fallback(args)

        if stderr:
            sys.stderr.write(stderr)

        if returncode == 0:
            if stdout.strip():
                saved_path = save_output_to_file(
                    args["prompt"], stdout, is_fallback=True
                )
                if saved_path:
                    log_info(f"Fallback output saved to {saved_path}")
            sys.exit(0)
        else:
            log_error(f"Fallback failed with code {returncode}")
            sys.exit(returncode)

    # 首先尝试运行 Gemini CLI
    returncode, stdout, stderr = run_gemini(args)

    # 输出 stderr
    if stderr:
        sys.stderr.write(stderr)

    # 检查是否需要降级
    if returncode != 0 and should_fallback(stderr, returncode):
        log_warn(f"Gemini CLI failed with code {returncode}, triggering fallback")

        # 运行降级方案
        fallback_returncode, fallback_stdout, fallback_stderr = run_fallback(args)

        if fallback_stderr:
            sys.stderr.write(fallback_stderr)

        if fallback_returncode == 0:
            # 保存降级输出
            if fallback_stdout.strip():
                saved_path = save_output_to_file(
                    args["prompt"], fallback_stdout, is_fallback=True
                )
                if saved_path:
                    log_info(f"Fallback output saved to {saved_path}")
            sys.exit(0)
        else:
            log_error(f"Fallback also failed with code {fallback_returncode}")
            sys.exit(fallback_returncode)

    elif returncode != 0:
        # 非降级错误，直接退出
        log_error(f"Gemini exited with status {returncode}")
        sys.exit(returncode)

    else:
        # Gemini CLI 成功
        if stdout.strip():
            saved_path = save_output_to_file(args["prompt"], stdout, is_fallback=False)
            if saved_path:
                log_info(f"Output saved to {saved_path}")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
