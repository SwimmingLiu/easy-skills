#!/usr/bin/env python3
"""Probe the status of a dispatched agent task.

Usage:
    python3 monitor-agent.py <task-id>

Exit codes:
    0  Task is still running.
    1  Task is complete and the temporary cron job can be removed.
    2  Task is failed and should be escalated to the user.
    3  Monitoring itself failed and should be escalated to the user.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO_ROOT = Path("/home/admin/openclaw/workspace")
DEFAULT_WORKTREE_ROOT = Path("/home/admin/openclaw/agent-worktrees")
DEFAULT_TASK_REGISTRY = DEFAULT_REPO_ROOT / ".clawdbot" / "active-tasks.json"


def run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def detect_repo_root() -> Path:
    repo_root = Path(os.environ.get("REPO_ROOT", DEFAULT_REPO_ROOT))
    return repo_root.resolve()


def detect_base_branch(repo_root: Path) -> str:
    env_branch = os.environ.get("BASE_BRANCH")
    if env_branch:
        return env_branch

    code, stdout, _ = run(
        ["git", "-C", str(repo_root), "symbolic-ref", "refs/remotes/origin/HEAD"]
    )
    if code == 0 and stdout.startswith("refs/remotes/origin/"):
        return stdout.rsplit("/", 1)[-1]

    for candidate in ("main", "master"):
        code, _, _ = run(
            [
                "git",
                "-C",
                str(repo_root),
                "show-ref",
                "--verify",
                f"refs/remotes/origin/{candidate}",
            ]
        )
        if code == 0:
            return candidate

    return "main"


def tmux_session_alive(task_id: str) -> bool:
    code, _, _ = run(["tmux", "has-session", "-t", f"agent-{task_id}"])
    return code == 0


def tmux_current_command(task_id: str) -> str:
    code, output, _ = run(
        ["tmux", "display-message", "-p", "-t", f"agent-{task_id}", "#{pane_current_command}"]
    )
    if code != 0:
        return ""
    return output.strip()


def capture_recent_output(task_id: str, lines: int = 20) -> list[str]:
    code, output, _ = run(
        ["tmux", "capture-pane", "-pt", f"agent-{task_id}", "-S", f"-{lines}"]
    )
    if code != 0 or not output:
        return []
    return output.splitlines()[-5:]


def get_recent_commits(worktree: Path, base_branch: str) -> list[str]:
    if not worktree.exists():
        return []

    # 首先检查是否有 origin remote
    code, _, _ = run(["git", "-C", str(worktree), "remote", "get-url", "origin"])
    has_origin = code == 0

    if has_origin:
        # 尝试 fetch（静默失败）
        run(["git", "-C", str(worktree), "fetch", "origin", base_branch])

        code, merge_base, stderr = run(
            [
                "git",
                "-C",
                str(worktree),
                "merge-base",
                "HEAD",
                f"origin/{base_branch}",
            ]
        )
        if code != 0 or not merge_base:
            # 如果找不到 origin/base，尝试本地 base
            code, merge_base, _ = run(
                ["git", "-C", str(worktree), "merge-base", "HEAD", base_branch]
            )
    else:
        # 没有 origin，使用本地 base 分支
        code, merge_base, _ = run(
            ["git", "-C", str(worktree), "merge-base", "HEAD", base_branch]
        )

    if code != 0 or not merge_base:
        # 最后回退：直接列出最近 10 个提交
        code, log, _ = run(
            ["git", "-C", str(worktree), "log", "--oneline", "--decorate=no", "-10"]
        )
        return log.splitlines() if log else []

    code, log, stderr = run(
        [
            "git",
            "-C",
            str(worktree),
            "log",
            "--oneline",
            "--decorate=no",
            f"{merge_base}..HEAD",
            "-10",
        ]
    )
    if code != 0:
        raise RuntimeError(f"Unable to read recent commits: {stderr}")

    return log.splitlines() if log else []


def get_pr_url(branch: str) -> str:
    code, stdout, _ = run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            "url",
            "--jq",
            ".[0].url",
        ]
    )
    if code != 0 or stdout in {"", "null"}:
        return ""
    return stdout


def load_task_registry(repo_root: Path) -> dict:
    registry = Path(os.environ.get("TASK_REGISTRY", DEFAULT_TASK_REGISTRY))
    if not registry.is_absolute():
        registry = (repo_root / registry).resolve()
    if not registry.exists():
        return {}
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid task registry JSON: {exc}") from exc

    if isinstance(payload, dict) and isinstance(payload.get("tasks"), dict):
        return payload["tasks"]
    if isinstance(payload, dict):
        return payload
    raise RuntimeError("Task registry must be a JSON object")


def build_status(task_id: str) -> tuple[int, dict]:
    repo_root = detect_repo_root()
    worktree_root = Path(os.environ.get("WORKTREE_ROOT", DEFAULT_WORKTREE_ROOT))
    worktree = (worktree_root / task_id).resolve()
    branch = f"agent/{task_id}"

    registry = load_task_registry(repo_root)
    task = registry.get(task_id, {})
    base_branch = task.get("baseBranch") or detect_base_branch(repo_root)

    alive = tmux_session_alive(task_id)
    current_command = tmux_current_command(task_id) if alive else ""
    recent_output = capture_recent_output(task_id) if alive else []
    pr_url = get_pr_url(branch)
    commits = get_recent_commits(worktree, base_branch)

    status = {
        "task_id": task_id,
        "branch": branch,
        "base_branch": base_branch,
        "worktree": str(worktree),
        "session_alive": alive,
        "pane_current_command": current_command,
        "pr_url": pr_url,
        "recent_commits": commits,
        "recent_output_lines": recent_output,
        "registry_status": task.get("status"),
    }

    if pr_url:
        status["state"] = "complete"
        status["message"] = "PR detected; remove the temporary cron job."
        return 1, status

    recent_output_text = "\n".join(recent_output)
    runner_failed = (
        alive
        and current_command in {"bash", "sh", "zsh"}
        and (
            "No such file or directory" in recent_output_text
            or "未知 Agent 类型" in recent_output_text
            or "command not found" in recent_output_text
        )
    )

    if runner_failed:
        status["state"] = "failed"
        status["message"] = (
            "Tmux session is still open, but the runner appears to have failed and returned to the shell; escalate to the user."
        )
        return 2, status

    if alive:
        status["state"] = "running"
        if commits:
            status["message"] = "Agent is running and has produced commits."
        else:
            status["message"] = "Agent is running; no commits yet."
        return 0, status

    if commits:
        status["state"] = "complete"
        status["message"] = (
            "Tmux session ended after producing commits; remove the cron job and "
            "report likely completion."
        )
        return 1, status

    status["state"] = "failed"
    status["message"] = (
        "Tmux session ended without a PR or commits; escalate to the user."
    )
    return 2, status


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: monitor-agent.py <task-id>", file=sys.stderr)
        return 3

    task_id = sys.argv[1]

    try:
        exit_code, status = build_status(task_id)
    except Exception as exc:  # pragma: no cover - defensive CLI handling
        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "state": "error",
                    "message": str(exc),
                },
                indent=2,
            )
        )
        return 3

    print(json.dumps(status, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
