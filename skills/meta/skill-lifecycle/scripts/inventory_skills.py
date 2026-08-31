#!/usr/bin/env python3
"""Create a deterministic inventory of Agent Skill packages."""

import argparse
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
PLAIN_SCALAR_RESERVED_START = frozenset("-?:,[]{}#&*!|>'\"%@`")
PLAIN_NON_STRING = re.compile(
    r"(?:~|null|true|false|yes|no|on|off"
    r"|[-+]?(?:\.inf|\.nan|0b[01_]+|0o[0-7_]+|0x[0-9a-f_]+"
    r"|[0-9][0-9_]*(?:\.[0-9_]*)?(?:e[-+]?[0-9]+)?))\Z",
    re.IGNORECASE,
)


class FrontmatterError(ValueError):
    def __init__(self, message, line=1):
        super().__init__(message)
        self.line = line


def _strip_inline_comment(value):
    quote = None
    index = 0
    while index < len(value):
        character = value[index]
        if quote == '"':
            if character == "\\":
                index += 2
                continue
            if character == '"':
                quote = None
        elif quote == "'":
            if character == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 2
                    continue
                quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value


def _parse_scalar(value):
    value = _strip_inline_comment(value).strip()
    if not value:
        return None
    if value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            raise ValueError("single-quoted scalar is not closed")
        parsed = []
        index = 1
        while index < len(value) - 1:
            character = value[index]
            if character == "'":
                if index + 1 < len(value) - 1 and value[index + 1] == "'":
                    parsed.append("'")
                    index += 2
                    continue
                raise ValueError("single-quoted scalar contains trailing content")
            parsed.append(character)
            index += 1
        return "".join(parsed)
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("double-quoted scalar is malformed") from error
        if not isinstance(parsed, str):
            raise ValueError("double-quoted scalar must contain text")
        return parsed
    if value.startswith(("[", "{")):
        expected = "]" if value.startswith("[") else "}"
        if not value.endswith(expected):
            raise ValueError("inline collection is malformed")
        return [] if expected == "]" else {}
    if value[0] in PLAIN_SCALAR_RESERVED_START:
        raise ValueError("plain scalar starts with a reserved indicator")
    if ": " in value:
        raise ValueError("plain scalar contains an unquoted mapping separator")
    if PLAIN_NON_STRING.fullmatch(value):
        raise ValueError("plain scalar would resolve to a non-string YAML value")
    return value


def parse_frontmatter(text, with_lines=False):
    """Parse a strict top-level YAML subset and skip nested extra fields."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise FrontmatterError("frontmatter must start with ---")
    try:
        closing = next(
            index for index, line in enumerate(lines[1:], 1) if line == "---"
        )
    except StopIteration as error:
        raise FrontmatterError(
            "frontmatter is missing its closing --- delimiter"
        ) from error
    metadata = {}
    metadata_lines = {}
    index = 1
    while index < closing:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", line)
        if not match:
            raise FrontmatterError(
                f"frontmatter line {index + 1} is not a mapping entry", index + 1
            )
        key, raw_value = match.group(1), (match.group(2) or "")
        if key in metadata:
            raise FrontmatterError(f"frontmatter key is duplicated: {key}", index + 1)
        metadata_lines[key] = index + 1
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
        if not raw_value:
            nested_lines = []
            index += 1
            while index < closing and (
                not lines[index].strip() or lines[index].startswith((" ", "\t"))
            ):
                if lines[index].strip():
                    nested_lines.append(lines[index].lstrip())
                index += 1
            if not nested_lines:
                metadata[key] = None
            elif nested_lines[0].startswith("- "):
                metadata[key] = []
            else:
                metadata[key] = {}
            continue
        try:
            metadata[key] = _parse_scalar(raw_value)
        except ValueError as error:
            raise FrontmatterError(str(error), index + 1) from error
        index += 1
    return (metadata, metadata_lines) if with_lines else metadata


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
    """Atomically replace path and return whether parent durability was confirmed."""
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
        directory_descriptor = None
        try:
            directory_descriptor = os.open(destination.parent, os.O_RDONLY)
            os.fsync(directory_descriptor)
        except OSError:
            return False
        finally:
            if directory_descriptor is not None:
                os.close(directory_descriptor)
        return True
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
            durable = atomic_write_text(options.output, content)
            if not durable:
                print(
                    "warning: inventory output was committed, but directory durability "
                    "could not be confirmed",
                    file=sys.stderr,
                )
        else:
            sys.stdout.write(content)
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"inventory_skills: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
