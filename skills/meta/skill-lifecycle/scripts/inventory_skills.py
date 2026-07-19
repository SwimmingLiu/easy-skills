#!/usr/bin/env python3
"""Create a deterministic inventory of Agent Skill packages."""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1
EXCLUDED_DIRECTORIES = {
    ".git",
    ".worktrees",
    "node_modules",
    "__pycache__",
    ".cache",
}


def _parse_scalar(value):
    value = value.strip()
    if not value:
        return None
    if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        return parsed
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return []
        return parsed if isinstance(parsed, list) else []
    if value.startswith("{") and value.endswith("}"):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    lowered = value.lower()
    if lowered in {"null", "~"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def parse_frontmatter(text):
    """Parse the simple top-level YAML mapping used by Skill frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with ---")
    try:
        closing = next(
            index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise ValueError("frontmatter is missing its closing --- delimiter") from error
    metadata = {}
    index = 1
    while index < closing:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", line)
        if not match:
            raise ValueError(f"frontmatter line {index + 1} is not a mapping entry")
        key, raw_value = match.group(1), (match.group(2) or "")
        if key in metadata:
            raise ValueError(f"frontmatter key is duplicated: {key}")
        if raw_value in {">", "|", ">-", "|-", ">+", "|+"}:
            fragments = []
            index += 1
            while index < closing and (
                not lines[index].strip() or lines[index].startswith((" ", "\t"))
            ):
                fragments.append(lines[index].strip())
                index += 1
            separator = " " if raw_value.startswith(">") else "\n"
            metadata[key] = separator.join(fragments).strip()
            continue
        metadata[key] = _parse_scalar(raw_value)
        index += 1
    return metadata


def discover_skill_files(root):
    """Yield non-symlink SKILL.md files below root in POSIX path order."""
    found = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directory_names[:] = [
            name
            for name in directory_names
            if name not in EXCLUDED_DIRECTORIES
            and not name.startswith(".")
            and not (current_path / name).is_symlink()
        ]
        if "SKILL.md" not in file_names:
            continue
        candidate = current_path / "SKILL.md"
        if candidate.is_file() and not candidate.is_symlink():
            found.append(candidate)
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def build_inventory(root, source=None, ref=None, license_name=None, hosts=()):
    records = []
    for path in discover_skill_files(root):
        content = path.read_bytes()
        try:
            metadata = parse_frontmatter(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            metadata = {}
        name = metadata.get("name")
        records.append(
            {
                "name": name if isinstance(name, str) else None,
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "source": source,
                "ref": ref,
                "license": license_name,
                "hosts": list(hosts),
            }
        )
    return {"schema_version": SCHEMA_VERSION, "skills": records}


def render_json(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def _markdown_cell(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(document):
    lines = [
        "# Skill Inventory",
        "",
        f"Schema version: {document['schema_version']}",
        "",
        "| Name | Path | SHA-256 | Source | Ref | License | Hosts |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in document["skills"]:
        values = (
            record["name"],
            record["path"],
            record["sha256"],
            record["source"],
            record["ref"],
            record["license"],
            record["hosts"],
        )
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def atomic_write_text(path, content):
    destination = Path(path)
    if destination.is_symlink():
        raise OSError(f"refusing symlink output path: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.is_symlink():
            raise OSError(f"refusing symlink output path: {destination}")
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="root directory to inventory")
    parser.add_argument("--output", help="write output atomically instead of stdout")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--source", help="default source metadata")
    parser.add_argument("--ref", help="default source revision metadata")
    parser.add_argument("--license", dest="license_name", help="default license metadata")
    parser.add_argument("--host", action="append", default=[], help="supported host; repeatable")
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    try:
        root = Path(options.root)
        if not root.is_dir():
            raise ValueError(f"inventory root is not a directory: {root}")
        if root.is_symlink():
            raise ValueError(f"inventory root must not be a symlink: {root}")
        root = root.resolve()
        document = build_inventory(
            root,
            source=options.source,
            ref=options.ref,
            license_name=options.license_name,
            hosts=options.host,
        )
        content = render_json(document) if options.format == "json" else render_markdown(document)
        if options.output:
            atomic_write_text(options.output, content)
        else:
            sys.stdout.write(content)
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"inventory_skills: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
