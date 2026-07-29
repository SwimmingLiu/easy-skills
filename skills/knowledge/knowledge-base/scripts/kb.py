#!/usr/bin/env python3
"""Deterministic plumbing for a Codex-native Markdown knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path


REQUIRED_DIRS = (
    "00-system",
    "01-inbox",
    "02-sources",
    "03-wiki/concepts",
    "04-projects",
    "08-journal",
)
SOURCE_FIELDS = (
    "id",
    "type",
    "status",
    "source_type",
    "source_url",
    "author",
    "published",
    "captured",
    "created",
    "updated",
    "sensitivity",
    "content_hash",
)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def locate(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file() and all(
            (candidate / item).is_dir() for item in REQUIRED_DIRS
        ):
            return candidate
    raise FileNotFoundError("no knowledge vault found in this directory or its parents")


def vault_path(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else locate(Path.cwd())


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", normalized, flags=re.UNICODE).strip("-")
    return slug or "untitled"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def content_hash(text: str) -> str:
    normalized = text.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_by_hash(root: Path, digest: str) -> Path | None:
    marker = f"content_hash: {digest}"
    for path in sorted((root / "02-sources").glob("*.md")):
        if marker in path.read_text(encoding="utf-8"):
            return path
    return None


def wiki_link(root: Path, path: Path) -> str:
    return f"[[{path.relative_to(root).with_suffix('').as_posix()}]]"


def append_once(path: Path, marker: str, block: str) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in current:
        return False
    separator = "" if not current or current.endswith("\n\n") else "\n"
    path.write_text(current + separator + block.rstrip() + "\n", encoding="utf-8")
    return True


def write_concept(root: Path, title: str, source_link: str, today: str) -> Path:
    path = root / "03-wiki" / "concepts" / f"{title}.md"
    if not path.exists():
        path.write_text(
            "\n".join(
                (
                    "---",
                    f"id: {slugify(title)}",
                    "type: concept",
                    "status: active",
                    f"created: {today}",
                    f"updated: {today}",
                    "confidence: medium",
                    "sources:",
                    f"  - {yaml_quote(source_link)}",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Current Synthesis",
                    "",
                    "This concept was captured for Codex synthesis.",
                    "",
                    "## Evidence",
                    "",
                    f"- {source_link}",
                    "",
                    "## Contradictions",
                    "",
                    "## Open Questions",
                    "",
                    "## Related",
                    "",
                )
            ),
            encoding="utf-8",
        )
    else:
        append_once(path, source_link, f"\n- {source_link}")
    return path


def ingest(args: argparse.Namespace) -> dict:
    root = vault_path(args.vault)
    digest = content_hash(args.text)
    existing = source_by_hash(root, digest)
    today = date.today().isoformat()
    created = existing is None

    if existing is None:
        short_hash = digest[:8]
        source_id = f"{today.replace('-', '')}-{slugify(args.title)}-{short_hash}"
        source_path = root / "02-sources" / f"{today} {args.title}.md"
        if source_path.exists():
            source_path = root / "02-sources" / f"{today} {args.title} {short_hash}.md"
        source_path.write_text(
            "\n".join(
                (
                    "---",
                    f"id: {source_id}",
                    "type: source",
                    "status: verified",
                    f"source_type: {args.source_type}",
                    f"source_url: {yaml_quote(args.source_url)}",
                    f"author: {yaml_quote(args.author)}",
                    f"published: {yaml_quote(args.published)}",
                    f"captured: {today}",
                    f"created: {today}",
                    f"updated: {today}",
                    f"sensitivity: {args.sensitivity}",
                    f"content_hash: {digest}",
                    "---",
                    "",
                    f"# {args.title}",
                    "",
                    "## Preserved Content",
                    "",
                    args.text.strip(),
                    "",
                    "## Provenance",
                    "",
                    f"- URL: {args.source_url or 'unknown'}",
                    f"- Author: {args.author}",
                    f"- Published: {args.published}",
                    f"- Captured: {today}",
                    "",
                    "## Processing Notes",
                    "",
                )
            ),
            encoding="utf-8",
        )
    else:
        source_path = existing

    source_link = wiki_link(root, source_path)
    if created:
        append_once(
            root / "02-sources" / "Sources Index.md",
            source_link,
            f"- {source_link} | {args.source_url or 'local fragment'}",
        )
        append_once(
            root / "08-journal" / "Knowledge Log.md",
            source_link,
            f"\n## [{today}] ingest | {args.title}\n\n- Preserved {source_link}.",
        )

    concepts = [write_concept(root, title, source_link, today) for title in args.concept]
    return {
        "created": created,
        "source_path": source_path.relative_to(root).as_posix(),
        "source_link": source_link,
        "content_hash": digest,
        "concept_paths": [path.relative_to(root).as_posix() for path in concepts],
    }


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def note_title(path: Path, text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else path.stem


def search(args: argparse.Namespace) -> dict:
    root = vault_path(args.vault)
    tokens = [token for token in re.split(r"\s+", args.query.lower()) if token]
    scored = []
    search_roots = ("03-wiki", "04-projects", "02-sources")
    for relative in search_roots:
        for path in (root / relative).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            score = sum(lowered.count(token) for token in tokens)
            if not score:
                continue
            links = [f"[[{item.split('|', 1)[0].split('#', 1)[0]}]]" for item in WIKILINK_RE.findall(text)]
            source_links = [link for link in links if link.startswith("[[02-sources/")]
            snippet_source = re.sub(r"\s+", " ", text.replace("---", " ")).strip()
            scored.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "title": note_title(path, text),
                    "score": score,
                    "snippet": snippet_source[:240],
                    "source_links": sorted(set(source_links)),
                    "source_url": parse_frontmatter(text).get("source_url", ""),
                }
            )
    scored.sort(key=lambda item: (-item["score"], item["path"]))
    results = scored[: args.limit]
    return {"query": args.query, "count": len(results), "results": results}


def resolve_link(root: Path, link: str, stems: dict[str, list[Path]]) -> bool:
    target = link.split("|", 1)[0].split("#", 1)[0].strip()
    if not target or "{{" in target:
        return True
    explicit = root / f"{target}.md"
    if explicit.is_file():
        return True
    return len(stems.get(Path(target).name.casefold(), [])) == 1


def check_vault(args: argparse.Namespace) -> tuple[dict, int]:
    root = vault_path(args.vault)
    issues = []
    for relative in REQUIRED_DIRS:
        if not (root / relative).is_dir():
            issues.append(f"missing required directory: {relative}")

    markdown = sorted(path for path in root.rglob("*.md") if ".git" not in path.parts)
    stems: dict[str, list[Path]] = {}
    for path in markdown:
        stems.setdefault(path.stem.casefold(), []).append(path)

    ids: dict[str, Path] = {}
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        fields = parse_frontmatter(text)
        if path.parent == root / "02-sources" and path.name not in {"AGENTS.md", "Sources Index.md"}:
            for field in SOURCE_FIELDS:
                if not fields.get(field):
                    issues.append(f"{path.relative_to(root)}: missing source field {field}")
        record_id = fields.get("id")
        if record_id:
            if record_id in ids:
                issues.append(
                    f"duplicate id {record_id}: {ids[record_id].relative_to(root)} and {path.relative_to(root)}"
                )
            ids[record_id] = path
        for link in WIKILINK_RE.findall(text):
            if not resolve_link(root, link, stems):
                issues.append(f"{path.relative_to(root)}: unresolved wikilink [[{link}]]")

    report = {"healthy": not issues, "vault": str(root), "notes_checked": len(markdown), "issues": issues}
    return report, 0 if not issues else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    locate_parser = commands.add_parser("locate")
    locate_parser.add_argument("--start", default=".")

    ingest_parser = commands.add_parser("ingest")
    ingest_parser.add_argument("--vault")
    ingest_parser.add_argument("--title", required=True)
    ingest_parser.add_argument("--text", required=True)
    ingest_parser.add_argument("--source-url", default="")
    ingest_parser.add_argument("--source-type", default="fragment")
    ingest_parser.add_argument("--author", default="unknown")
    ingest_parser.add_argument("--published", default="unknown")
    ingest_parser.add_argument("--sensitivity", choices=("public", "internal", "private"), default="internal")
    ingest_parser.add_argument("--concept", action="append", default=[])

    search_parser = commands.add_parser("search")
    search_parser.add_argument("--vault")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)

    check_parser = commands.add_parser("check")
    check_parser.add_argument("--vault")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "locate":
            print(locate(Path(args.start)))
            return 0
        if args.command == "ingest":
            print(json.dumps(ingest(args), ensure_ascii=False, indent=2))
            return 0
        if args.command == "search":
            print(json.dumps(search(args), ensure_ascii=False, indent=2))
            return 0
        report, status = check_vault(args)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return status
    except (FileNotFoundError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
