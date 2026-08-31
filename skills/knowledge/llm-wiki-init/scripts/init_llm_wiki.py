#!/usr/bin/env python3
"""Initialize an additive, source-backed local LLM Wiki."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


DIRECTORIES = (
    "raw",
    "raw/articles",
    "raw/news",
    "raw/papers",
    "raw/reports",
    "raw/twitter",
    "raw/twitters",
    "raw/wechat",
    "raw/records",
    "raw/youtube-transcript",
    "raw/xiaoyuzhou",
    "raw/video",
    "wiki",
    "wiki/sources",
    "wiki/topics",
    "wiki/entities",
    "wiki/analyses",
    "wiki/decisions",
    "wiki/indexes",
    "index",
    "outputs",
    "assets",
    "scripts",
)

TEMPLATE_FILES = {
    "AGENTS.md": "AGENTS.md",
    "README.md": "README.md",
    "SHARE_CHECKLIST.md": "SHARE_CHECKLIST.md",
    ".gitignore": ".gitignore",
    "wiki/index.md": "wiki/index.md",
    "wiki/overview.md": "wiki/overview.md",
    "wiki/log.md": "wiki/log.md",
    "wiki/sources/README.md": "wiki/sources/README.md",
    "wiki/topics/README.md": "wiki/topics/README.md",
    "wiki/entities/README.md": "wiki/entities/README.md",
    "wiki/analyses/README.md": "wiki/analyses/README.md",
    "wiki/decisions/README.md": "wiki/decisions/README.md",
    "wiki/indexes/raw-status.md": "wiki/indexes/raw-status.md",
    "index/home.md": "index/home.md",
    "scripts/rebuild_kb_indexes.rb": "scripts/rebuild_kb_indexes.rb",
    "scripts/kb_lint.rb": "scripts/kb_lint.rb",
    "scripts/privacy_scan.sh": "scripts/privacy_scan.sh",
}

TRACKED_EMPTY_DIRS = (
    "raw/articles",
    "raw/news",
    "raw/papers",
    "raw/reports",
    "raw/twitter",
    "raw/twitters",
    "raw/wechat",
    "raw/records",
    "raw/youtube-transcript",
    "raw/xiaoyuzhou",
    "raw/video",
    "outputs",
    "assets",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a non-destructive LLM Wiki skeleton to a directory."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory (default: current directory).",
    )
    parser.add_argument(
        "--title",
        help="Wiki title (default: target directory name).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned additions without writing anything.",
    )
    return parser.parse_args()


def render(template_path: Path, title: str, today: str) -> str:
    return (
        template_path.read_text(encoding="utf-8")
        .replace("{{VAULT_TITLE}}", title)
        .replace("{{DATE}}", today)
    )


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    title = args.title.strip() if args.title and args.title.strip() else target.name
    today = date.today().isoformat()
    templates = Path(__file__).resolve().parent.parent / "assets" / "templates"

    missing_templates = [
        str(templates / source)
        for source in TEMPLATE_FILES.values()
        if not (templates / source).is_file()
    ]
    if missing_templates:
        raise SystemExit("Missing template files: " + ", ".join(missing_templates))

    additions: list[tuple[str, Path, Path | None]] = []
    skipped: list[Path] = []

    if not target.exists():
        additions.append(("directory", target, None))

    for relative in DIRECTORIES:
        path = target / relative
        if not path.exists():
            additions.append(("directory", path, None))

    for destination, source in TEMPLATE_FILES.items():
        path = target / destination
        if path.exists():
            skipped.append(path)
        else:
            additions.append(("file", path, templates / source))

    for relative in TRACKED_EMPTY_DIRS:
        path = target / relative / ".gitkeep"
        if not path.exists():
            additions.append(("empty-file", path, None))

    mode = "DRY RUN" if args.dry_run else "WRITE"
    print(f"[{mode}] target: {target}")
    print(f"[{mode}] title: {title}")

    if args.dry_run:
        for kind, path, _ in additions:
            print(f"CREATE {kind}: {path}")
    else:
        target.mkdir(parents=True, exist_ok=True)
        for relative in DIRECTORIES:
            (target / relative).mkdir(parents=True, exist_ok=True)
        for kind, path, source in additions:
            if kind == "directory":
                path.mkdir(parents=True, exist_ok=True)
            elif kind == "file" and source is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(render(source, title, today), encoding="utf-8")
                if path.suffix in {".sh", ".rb"}:
                    path.chmod(path.stat().st_mode | 0o111)
            elif kind == "empty-file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)

    for path in skipped:
        print(f"SKIP existing file: {path}")

    print(f"Planned additions: {len(additions)}")
    print(f"Existing template files preserved: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
