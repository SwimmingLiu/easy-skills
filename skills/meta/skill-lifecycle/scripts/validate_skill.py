#!/usr/bin/env python3
"""Statically validate one Agent Skill package."""

import argparse
import ast
import os
import re
import string
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from inventory_skills import atomic_write_text, parse_frontmatter, render_json


SCHEMA_VERSION = 1
SEVERITIES = ("Blocker", "High", "Medium", "Low")
SEVERITY_ORDER = {severity: index for index, severity in enumerate(SEVERITIES)}
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
REFERENCE_DEFINITION = re.compile(r"^[ ]{0,3}\[([^\]\n]+)\]:\s*(.+?)\s*$")
REFERENCE_USAGE = re.compile(r"(?<!!)\[([^\]\n]+)\]\[([^\]\n]*)\]")
PLACEHOLDER_PATTERNS = (
    re.compile(r"\b" + "TO" + r"DO\b", re.IGNORECASE),
    re.compile(r"\b" + "TB" + r"D\b", re.IGNORECASE),
    re.compile(r"\{\{[^{}\n]+\}\}"),
    re.compile(r"\[DATA\s+NEEDED\]", re.IGNORECASE),
    re.compile(r"Lorem\s+ipsum", re.IGNORECASE),
)
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".bash", ".zsh", ".json", ".yaml", ".yml"}
IGNORED_DIRECTORIES = {".git", ".worktrees", "node_modules", "__pycache__", ".cache"}
MAX_TEXT_FILES = 1000
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 10_000_000
ANY_FENCE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(?:.*)$")
SHELL_FENCE = re.compile(
    r"^[ ]{0,3}(`{3,}|~{3,})\s*(?:bash|sh|shell|zsh|console)(?:\s+.*)?$",
    re.IGNORECASE,
)
DISCLOSURE_PATTERN = re.compile(
    r"(?:ask|request|obtain|require).{0,80}(?:permission|confirmation|consent|approval).{0,40}before"
    r"|before.{0,80}(?:ask|request|obtain|require).{0,40}(?:permission|confirmation|consent|approval)",
    re.IGNORECASE | re.DOTALL,
)
NEGATED_DISCLOSURE = re.compile(
    r"\b(?:never|do\s+not|don't|without)\b|不要|无需|不必", re.IGNORECASE
)
SAFE_PREREQUISITE_DISCLOSURE = re.compile(
    r"\b(?:never|do\s+not|don't)\b.{0,120}\bbefore\s+"
    r"(?:asking|requesting|obtaining).{0,40}(?:permission|confirmation|consent|approval)",
    re.IGNORECASE | re.DOTALL,
)
RISK_DISCLOSURE_TERMS = {
    "RISK_DESTRUCTIVE_RM": re.compile(
        r"\brm\b|\b(?:remove|removing|delete|deleting)\b", re.I
    ),
    "RISK_NETWORK_UPLOAD": re.compile(r"\b(?:upload|curl|wget)\b", re.I),
    "RISK_GIT_PUSH": re.compile(
        r"\bgit\s+push\b|\bpush(?:ing)?\s+(?:changes?\s+)?to\s+(?:the\s+)?remote\b",
        re.I,
    ),
    "RISK_GLOBAL_INSTALL": re.compile(
        r"\b(?:npm|pnpm|yarn|pip|pipx)\b.{0,40}\b(?:install|add)\b"
        r"|\bglobal(?:ly)?\b.{0,20}\b(?:install|package)\b"
        r"|\b(?:install|add)\b.{0,20}\bglobal(?:ly)?\b",
        re.I,
    ),
    "RISK_CREDENTIAL_READ": re.compile(
        r"\b(?:credential|secret|token|key|id_rsa|id_ed25519)\b|\.ssh(?:/|\b)",
        re.I,
    ),
}
RISK_RULES = (
    (
        "RISK_DESTRUCTIVE_RM",
        "destructive rm command",
        re.compile(
            r"(?:^|[;&|]\s*)(?:sudo\s+)?rm\b"
            r"(?=[^\n]*(?:--recursive\b|-[A-Za-z]*r))"
            r"(?=[^\n]*(?:--force\b|-[A-Za-z]*f))"
        ),
    ),
    (
        "RISK_NETWORK_UPLOAD",
        "network upload command",
        re.compile(
            r"\b(?:curl\b[^\n]*(?:\s(?:-X\s*(?:POST|PUT|PATCH)|--request\s+(?:POST|PUT|PATCH)|-d\b|--data\b|-F\b|--form\b|-T\b|--upload-file\b))"
            r"|wget\b[^\n]*(?:--post-data|--post-file|--method[=\s]+(?:POST|PUT|PATCH)))",
            re.IGNORECASE,
        ),
    ),
    ("RISK_GIT_PUSH", "git push command", re.compile(r"(?:^|[;&|]\s*)git\s+push\b")),
    (
        "RISK_GLOBAL_INSTALL",
        "global package installation",
        re.compile(
            r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:npm|pnpm|yarn)\s+(?:install|add)\b[^\n]*(?:\s-g\b|--global\b)"
            r"|(?:^|[;&|]\s*)sudo\s+(?:python\s+-m\s+)?pip\s+install\b"
            r"|(?:^|[;&|]\s*)pipx\s+install\b"
        ),
    ),
    (
        "RISK_CREDENTIAL_READ",
        "credential or secret read",
        re.compile(
            r"(?:^|[;&|]\s*)(?:cat|less|more|head|tail|cp)\s+[^\n]*(?:~/\.ssh|~/\.aws|~/\.gnupg|\.env\b|credentials\b|id_rsa\b|id_ed25519\b)"
        ),
    ),
)


def finding(severity, code, message, path="SKILL.md", line=1):
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "line": line,
    }


def iter_files(root):
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORIES
            and not name.startswith(".")
            and not (current_path / name).is_symlink()
        )
        for name in sorted(file_names):
            path = current_path / name
            if path.is_file() and not path.is_symlink():
                yield path


def read_text_files(
    root,
    max_files=MAX_TEXT_FILES,
    max_file_bytes=MAX_FILE_BYTES,
    max_total_bytes=MAX_TOTAL_BYTES,
):
    """Read eligible text within deterministic package resource limits."""
    values = []
    findings = []
    file_count = 0
    total_bytes = 0
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative_path = path.relative_to(root).as_posix()
        file_count += 1
        if file_count > max_files:
            findings.append(
                finding("High", "RESOURCE_FILE_COUNT", "text file count exceeds limit", ".", 1)
            )
            break
        file_size = path.stat().st_size
        if file_size > max_file_bytes:
            findings.append(
                finding("High", "RESOURCE_FILE_SIZE", "text file exceeds byte limit", relative_path, 1)
            )
            continue
        if total_bytes + file_size > max_total_bytes:
            findings.append(
                finding("High", "RESOURCE_TOTAL_SIZE", "package text exceeds byte limit", relative_path, 1)
            )
            break
        content_bytes = path.read_bytes()
        if len(content_bytes) > max_file_bytes:
            findings.append(
                finding("High", "RESOURCE_FILE_SIZE", "text file exceeds byte limit", relative_path, 1)
            )
            continue
        if total_bytes + len(content_bytes) > max_total_bytes:
            findings.append(
                finding("High", "RESOURCE_TOTAL_SIZE", "package text exceeds byte limit", relative_path, 1)
            )
            break
        total_bytes += len(content_bytes)
        try:
            values.append((path, content_bytes.decode("utf-8")))
        except UnicodeDecodeError:
            findings.append(
                finding("High", "FILE_ENCODING", "eligible text file is not valid UTF-8", relative_path, 1)
            )
    return values, findings


def validate_frontmatter(root, skill_text):
    findings = []
    try:
        metadata, metadata_lines = parse_frontmatter(skill_text, with_lines=True)
    except ValueError as error:
        return {}, [
            finding(
                "Blocker",
                "FRONTMATTER_INVALID",
                str(error),
                line=getattr(error, "line", 1),
            )
        ]
    for key in ("name", "description"):
        value = metadata.get(key)
        if not isinstance(value, str):
            findings.append(
                finding(
                    "Blocker",
                    "REQUIRED_FIELD",
                    f"frontmatter {key} must be a string",
                    line=metadata_lines.get(key, 1),
                )
            )
        elif not value.strip():
            findings.append(
                finding(
                    "Blocker",
                    "REQUIRED_FIELD",
                    f"frontmatter {key} must be nonempty",
                    line=metadata_lines.get(key, 1),
                )
            )
    name = metadata.get("name")
    if isinstance(name, str):
        if not NAME_PATTERN.fullmatch(name):
            findings.append(
                finding(
                    "High",
                    "INVALID_NAME",
                    "frontmatter name must use lowercase letters, digits, and single hyphens",
                    line=metadata_lines.get("name", 1),
                )
            )
        if name != root.name:
            findings.append(
                finding(
                    "High",
                    "NAME_DIRECTORY_MISMATCH",
                    f"frontmatter name {name!r} does not match directory {root.name!r}",
                    line=metadata_lines.get("name", 1),
                )
            )
    return metadata, findings


def _link_target(raw_target):
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(None, 1)[0]
    unescaped = []
    index = 0
    while index < len(target):
        if (
            target[index] == "\\"
            and index + 1 < len(target)
            and target[index + 1] in string.punctuation
        ):
            unescaped.append(target[index + 1])
            index += 2
            continue
        unescaped.append(target[index])
        index += 1
    return unquote("".join(unescaped))


def _nonfenced_markdown_lines(content):
    fence_marker = None
    for line_number, line in enumerate(content.splitlines(), 1):
        if fence_marker:
            if re.fullmatch(
                r"[ ]{0,3}"
                + re.escape(fence_marker[0])
                + rf"{{{len(fence_marker)},}}[ \t]*",
                line,
            ):
                fence_marker = None
            continue
        fence = ANY_FENCE.match(line)
        if fence:
            fence_marker = fence.group(1)
            continue
        yield line_number, line


def _inline_link_targets(line):
    index = 0
    while index < len(line):
        opening = line.find("[", index)
        if opening < 0:
            return
        if opening > 0 and line[opening - 1] == "!":
            index = opening + 1
            continue
        label_end = line.find("]", opening + 1)
        if label_end < 0 or label_end + 1 >= len(line) or line[label_end + 1] != "(":
            index = opening + 1
            continue
        destination_start = label_end + 2
        if destination_start < len(line) and line[destination_start] == "<":
            destination_end = line.find(">", destination_start + 1)
            if destination_end >= 0:
                yield line[destination_start : destination_end + 1]
                index = destination_end + 1
                continue
        depth = 1
        cursor = destination_start
        while cursor < len(line):
            if line[cursor] == "\\" and cursor + 1 < len(line):
                cursor += 2
                continue
            if line[cursor] == "(":
                depth += 1
            elif line[cursor] == ")":
                depth -= 1
                if depth == 0:
                    yield line[destination_start:cursor]
                    index = cursor + 1
                    break
            cursor += 1
        else:
            return


def validate_links(root, text_files):
    findings = []
    resolved_root = root.resolve()
    for path, content in text_files:
        if path.suffix.lower() != ".md":
            continue
        relative_path = path.relative_to(root).as_posix()
        definitions = {}
        referenced = set()
        for line_number, line in _nonfenced_markdown_lines(content):
            definition = REFERENCE_DEFINITION.match(line)
            if definition:
                label = " ".join(definition.group(1).lower().split())
                definitions.setdefault(label, (definition.group(2), line_number))
            for usage in REFERENCE_USAGE.finditer(line):
                label = usage.group(2) or usage.group(1)
                referenced.add(" ".join(label.lower().split()))
            for raw_target in _inline_link_targets(line):
                target = _link_target(raw_target)
                findings.extend(
                    _validate_link_target(
                        target, path, resolved_root, relative_path, line_number
                    )
                )
        for label in sorted(referenced):
            if label not in definitions:
                continue
            raw_target, line_number = definitions[label]
            findings.extend(
                _validate_link_target(
                    _link_target(raw_target),
                    path,
                    resolved_root,
                    relative_path,
                    line_number,
                )
            )
    return findings


def _validate_link_target(target, source_path, resolved_root, relative_path, line_number):
    lowered = target.lower()
    if (
        not target
        or target.startswith("#")
        or lowered.startswith(("http://", "https://", "mailto:"))
    ):
        return []
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    candidate = (source_path.parent / path_part).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return [
            finding(
                "High",
                "LINK_PATH_ESCAPE",
                f"local link escapes skill root: {target}",
                relative_path,
                line_number,
            )
        ]
    if not candidate.exists():
        return [
            finding(
                "High",
                "BROKEN_LOCAL_LINK",
                f"local link target does not exist: {target}",
                relative_path,
                line_number,
            )
        ]
    return []


def validate_placeholders(root, text_files):
    findings = []
    for path, content in text_files:
        relative_path = path.relative_to(root).as_posix()
        if relative_path == "evals/baseline-observations.md":
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in PLACEHOLDER_PATTERNS):
                findings.append(
                    finding(
                        "High",
                        "PLACEHOLDER_TOKEN",
                        "unresolved template token",
                        relative_path,
                        line_number,
                    )
                )
    return findings


def _qualified_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _python_command_lines(content):
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    supported_calls = {
        "os.popen",
        "os.system",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
    }
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name in {"os", "subprocess"}:
                    aliases[imported.asname or imported.name] = imported.name
        elif isinstance(node, ast.ImportFrom) and node.module in {"os", "subprocess"}:
            for imported in node.names:
                aliases[imported.asname or imported.name] = f"{node.module}.{imported.name}"

    def resolved_name(node):
        qualified = _qualified_name(node)
        first, separator, remainder = qualified.partition(".")
        resolved = aliases.get(first, first)
        return f"{resolved}.{remainder}" if separator else resolved

    commands = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or resolved_name(node.func) not in supported_calls
            or not node.args
        ):
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            command = argument.value
        elif isinstance(argument, (ast.List, ast.Tuple)) and all(
            isinstance(item, ast.Constant) and isinstance(item.value, (str, int, float))
            for item in argument.elts
        ):
            command = " ".join(str(item.value) for item in argument.elts)
        else:
            continue
        commands.append((node.lineno, command))
    return sorted(commands)


def _join_shell_continuations(lines):
    pending_line = None
    pending_text = ""
    for line_number, text in lines:
        stripped = text.rstrip()
        if pending_line is None:
            pending_line = line_number
        pending_text += stripped[:-1].rstrip() + " " if stripped.endswith("\\") else stripped
        if stripped.endswith("\\"):
            continue
        yield pending_line, pending_text.strip()
        pending_line = None
        pending_text = ""
    if pending_line is not None:
        yield pending_line, pending_text.strip()


def command_lines(root, text_files):
    for path, content in text_files:
        relative_path = path.relative_to(root).as_posix()
        is_packaged_script = relative_path.startswith("scripts/")
        is_shell_script = is_packaged_script and path.suffix.lower() in {
            ".sh", ".bash", ".zsh"
        }
        is_python_script = is_packaged_script and path.suffix.lower() == ".py"
        if is_python_script:
            for line_number, command in _python_command_lines(content):
                yield relative_path, line_number, command, content
            continue
        segments = []
        if path.suffix.lower() == ".md":
            fence_marker = None
            shell_fence = False
            current_segment = []
            for line_number, line in enumerate(content.splitlines(), 1):
                if fence_marker is not None:
                    if re.fullmatch(
                        r"[ ]{0,3}"
                        + re.escape(fence_marker[0])
                        + rf"{{{len(fence_marker)},}}[ \t]*",
                        line,
                    ):
                        if current_segment:
                            segments.append(current_segment)
                        current_segment = []
                        fence_marker = None
                        shell_fence = False
                    elif shell_fence:
                        current_segment.append((line_number, line))
                    continue
                fence = ANY_FENCE.match(line)
                if fence:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = []
                    fence_marker = fence.group(1)
                    shell_fence = SHELL_FENCE.match(line) is not None
                    continue
                if line.lstrip().startswith("$ "):
                    if current_segment and current_segment[-1][0] + 1 != line_number:
                        segments.append(current_segment)
                        current_segment = []
                    current_segment.append(
                        (line_number, line.lstrip().removeprefix("$ "))
                    )
                elif current_segment:
                    segments.append(current_segment)
                    current_segment = []
            if current_segment:
                segments.append(current_segment)
        elif is_shell_script:
            segments = [list(enumerate(content.splitlines(), 1))]
        for segment in segments:
            for line_number, command in _join_shell_continuations(segment):
                yield relative_path, line_number, command, content


def _has_associated_disclosure(code, file_content, line_number):
    lines = file_content.splitlines()
    start = max(0, line_number - 7)
    for index in range(start, line_number - 1):
        line = lines[index]
        preceding_line_is_negated = (
            index > start and NEGATED_DISCLOSURE.search(lines[index - 1]) is not None
        )
        for clause in re.split(r"[.!?;。！？；]+", line):
            if not RISK_DISCLOSURE_TERMS[code].search(clause):
                continue
            if preceding_line_is_negated:
                continue
            if SAFE_PREREQUISITE_DISCLOSURE.search(clause):
                return True
            if NEGATED_DISCLOSURE.search(clause):
                continue
            if DISCLOSURE_PATTERN.search(clause):
                return True
    return False


def validate_risks(root, text_files):
    findings = []
    for relative_path, line_number, line, file_content in command_lines(root, text_files):
        for code, label, pattern in RISK_RULES:
            if pattern.search(line):
                disclosed = _has_associated_disclosure(code, file_content, line_number)
                severity = "Medium" if disclosed else "High"
                suffix = "; explicit permission is disclosed, but manual review remains" if disclosed else "; explicit permission is not disclosed"
                findings.append(
                    finding(severity, code, label + suffix, relative_path, line_number)
                )
    return findings


def validate_skill(root):
    skill_file = root / "SKILL.md"
    if not skill_file.is_file() or skill_file.is_symlink():
        findings = [
            finding("Blocker", "SKILL_FILE_MISSING", "skill directory must contain a regular SKILL.md")
        ]
    else:
        text_files, findings = read_text_files(root)
        skill_text = next(
            (content for path, content in text_files if path == skill_file), None
        )
        if skill_text is not None:
            _, frontmatter_findings = validate_frontmatter(root, skill_text)
            findings.extend(frontmatter_findings)
        findings.extend(validate_links(root, text_files))
        findings.extend(validate_placeholders(root, text_files))
        findings.extend(validate_risks(root, text_files))
    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["path"],
            item["line"],
            item["code"],
            item["message"],
        )
    )
    counts = Counter(item["severity"] for item in findings)
    failed = bool(counts["Blocker"] or counts["High"])
    return {
        "schema_version": SCHEMA_VERSION,
        "skill_path": str(root.resolve()),
        "status": "fail" if failed else "pass",
        "counts": {severity: counts[severity] for severity in SEVERITIES},
        "findings": findings,
    }


def _markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(document):
    lines = [
        "# Skill Validation",
        "",
        f"- Skill: `{document['skill_path']}`",
        f"- Status: **{document['status']}**",
        f"- Schema version: {document['schema_version']}",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {severity} | {document['counts'][severity]} |" for severity in SEVERITIES)
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "| Severity | Code | Path | Line | Message |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    if not document["findings"]:
        lines.append("| Low | NONE |  |  | No findings. |")
    for item in document["findings"]:
        values = (item["severity"], item["code"], item["path"], item["line"], item["message"])
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Static analysis is intentionally incomplete: dynamic shell wrappers, "
            "dynamic Python commands, and filesystem TOCTOU races are outside scope."
        ),
    )
    parser.add_argument("skill_directory", help="Skill package directory to validate")
    parser.add_argument("--output", help="write output atomically instead of stdout")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(arguments=None):
    options = build_parser().parse_args(arguments)
    try:
        root = Path(options.skill_directory)
        if not root.is_dir():
            raise ValueError(f"skill directory is not a directory: {root}")
        if root.is_symlink():
            raise ValueError(f"skill directory must not be a symlink: {root}")
        root = root.resolve()
        document = validate_skill(root)
        content = render_json(document) if options.format == "json" else render_markdown(document)
        if options.output:
            durable = atomic_write_text(options.output, content)
            if not durable:
                print(
                    "warning: validation output was committed, but directory durability "
                    "could not be confirmed",
                    file=sys.stderr,
                )
        else:
            sys.stdout.write(content)
        return 1 if document["status"] == "fail" else 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"validate_skill: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
