#!/usr/bin/env python3
"""Monitor a dispatched agent task.

Usage:
    python3 monitor-agent.py <task-id>

Exit codes:
    0  Task is still running (cron should continue).
    1  Task is complete (cron should delete itself).
    2  Task failed without a PR (triggers Ralph Loop).
"""

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def tmux_session_alive(task_id: str) -> bool:
    code, _ = run(["tmux", "has-session", "-t", f"agent-{task_id}"])
    return code == 0


def capture_recent_output(task_id: str, lines: int = 20) -> str:
    code, output = run(
        ["tmux", "capture-pane", "-pt", f"agent-{task_id}", "-S", f"-{lines}"]
    )
    return output if code == 0 else ""


def get_recent_commits(worktree: Path, branch: str) -> list[str]:
    code, log = run(
        [
            "git",
            "-C",
            str(worktree),
            "log",
            f"origin/main..{branch}",
            "--oneline",
            "--no-walk",
            "-10",
        ]
    )
    return log.splitlines() if code == 0 and log else []


def get_pr_url(branch: str) -> str:
    code, url = run(["gh", "pr", "view", branch, "--json", "url", "-q", ".url"])
    return url if code == 0 else ""


def load_task_registry(workspace: Path) -> dict:
    registry = workspace / ".clawdbot" / "active-tasks.json"
    if registry.exists():
        return json.loads(registry.read_text())
    return {}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: monitor-agent.py <task-id>", file=sys.stderr)
        return 2

    task_id = sys.argv[1]
    workspace = Path(__file__).resolve().parents[3]  # …/workspace
    worktree = workspace.parent / "agent-worktrees" / task_id
    branch = f"agent/{task_id}"

    tasks = load_task_registry(workspace)
    task = tasks.get(task_id, {})

    alive = tmux_session_alive(task_id)
    pr_url = get_pr_url(branch)
    commits = get_recent_commits(worktree, branch) if worktree.exists() else []
    recent_output = capture_recent_output(task_id) if alive else ""

    status = {
        "task_id": task_id,
        "session_alive": alive,
        "pr_url": pr_url,
        "recent_commits": commits,
        "recent_output_lines": recent_output.splitlines()[-5:] if recent_output else [],
    }

    print(json.dumps(status, indent=2))

    # Task complete: PR exists or session ended with commits
    if pr_url:
        print(f"[monitor] PR created: {pr_url} — task complete.")
        return 1  # signals cron to delete itself

    if not alive:
        if commits:
            print(
                f"[monitor] Session ended with {len(commits)} commit(s) — possible success, check manually."
            )
            return 1  # treat as done; agent may have exited cleanly
        else:
            print(
                "[monitor] Session ended without commits or PR — triggering Ralph Loop."
            )
            subprocess.Popen(
                [str(workspace / "scripts/agent-orchestration/ralph-loop.sh"), task_id],
                start_new_session=True,
            )
            return 2

    # Still running
    if commits:
        print(f"[monitor] Agent running — {len(commits)} commit(s) so far.")
    else:
        print("[monitor] Agent running — no commits yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
