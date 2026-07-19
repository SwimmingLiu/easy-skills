#!/usr/bin/env python3
"""Statically validate one Agent Skill package."""

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from inventory_skills import atomic_write_text, parse_frontmatter, render_json


SCHEMA_VERSION = 1
SEVERITIES = ("Blocker", "High", "Medium", "Low")
SEVERITY_ORDER = {severity: index for index, severity in enumerate(SEVERITIES)}
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")
PLACEHOLDER_PATTERNS = (
    re.compile(r"\b" + "TO" + r"DO\b", re.IGNORECASE),
    re.compile(r"\b" + "TB" + r"D\b", re.IGNORECASE),
    re.compile(r"\{\{[^{}\n]+\}\}"),
    re.compile(r"\[DATA\s+NEEDED\]", re.IGNORECASE),
    re.compile(r"Lorem\s+ipsum", re.IGNORECASE),
)
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".bash", ".zsh", ".json", ".yaml", ".yml"}
IGNORED_DIRECTORIES = {".git", ".worktrees", "node_modules", "__pycache__", ".cache"}
SHELL_FENCE = re.compile(r"^\s*```(?:bash|sh|shell|zsh|console)\s*$", re.IGNORECASE)
FENCE_END = re.compile(r"^\s*```\s*$")
PYTHON_PROCESS_CALL = re.compile(
    r"\b(?:subprocess\.(?:run|call|Popen|check_call|check_output)|os\.(?:system|popen))\s*\("
)
DISCLOSURE_PATTERN = re.compile(
    r"(?:ask|request|obtain|require).{0,80}(?:permission|confirmation|consent|approval).{0,40}before"
    r"|before.{0,80}(?:ask|request|obtain|require).{0,40}(?:permission|confirmation|consent|approval)",
    re.IGNORECASE | re.DOTALL,
)
RISK_RULES = (
    (
        "RISK_DESTRUCTIVE_RM",
        "destructive rm command",
        re.compile(
            r"(?:^|[;&|]\s*)rm\b"
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


def read_text_files(root):
    values = []
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            values.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return values


def validate_frontmatter(root, skill_text):
    findings = []
    try:
        metadata = parse_frontmatter(skill_text)
    except ValueError as error:
        return {}, [finding("Blocker", "FRONTMATTER_INVALID", str(error))]
    for key in ("name", "description"):
        value = metadata.get(key)
        if not isinstance(value, str):
            findings.append(
                finding("Blocker", "REQUIRED_FIELD", f"frontmatter {key} must be a string")
            )
        elif not value.strip():
            findings.append(
                finding("Blocker", "REQUIRED_FIELD", f"frontmatter {key} must be nonempty")
            )
    name = metadata.get("name")
    if isinstance(name, str):
        if not NAME_PATTERN.fullmatch(name):
            findings.append(
                finding(
                    "High",
                    "INVALID_NAME",
                    "frontmatter name must use lowercase letters, digits, and single hyphens",
                    line=2,
                )
            )
        if name != root.name:
            findings.append(
                finding(
                    "High",
                    "NAME_DIRECTORY_MISMATCH",
                    f"frontmatter name {name!r} does not match directory {root.name!r}",
                    line=2,
                )
            )
    return metadata, findings


def _link_target(raw_target):
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(None, 1)[0]
    return unquote(target)


def validate_links(root, text_files):
    findings = []
    resolved_root = root.resolve()
    for path, content in text_files:
        if path.suffix.lower() != ".md":
            continue
        relative_path = path.relative_to(root).as_posix()
        for line_number, line in enumerate(content.splitlines(), 1):
            for match in MARKDOWN_LINK.finditer(line):
                target = _link_target(match.group(1))
                lowered = target.lower()
                if not target or target.startswith("#") or lowered.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part = target.split("#", 1)[0].split("?", 1)[0]
                candidate = (path.parent / path_part).resolve()
                try:
                    candidate.relative_to(resolved_root)
                except ValueError:
                    findings.append(
                        finding(
                            "High",
                            "LINK_PATH_ESCAPE",
                            f"local link escapes skill root: {target}",
                            relative_path,
                            line_number,
                        )
                    )
                    continue
                if not candidate.exists():
                    findings.append(
                        finding(
                            "High",
                            "BROKEN_LOCAL_LINK",
                            f"local link target does not exist: {target}",
                            relative_path,
                            line_number,
                        )
                    )
    return findings


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


def command_lines(root, text_files):
    for path, content in text_files:
        relative_path = path.relative_to(root).as_posix()
        is_packaged_script = relative_path.startswith("scripts/")
        is_shell_script = is_packaged_script and path.suffix.lower() in {
            ".sh", ".bash", ".zsh"
        }
        is_python_script = is_packaged_script and path.suffix.lower() == ".py"
        in_shell_fence = False
        for line_number, line in enumerate(content.splitlines(), 1):
            if path.suffix.lower() == ".md":
                if SHELL_FENCE.match(line):
                    in_shell_fence = True
                    continue
                if in_shell_fence and FENCE_END.match(line):
                    in_shell_fence = False
                    continue
                command_shaped = in_shell_fence or line.lstrip().startswith("$ ")
            else:
                command_shaped = is_shell_script or (
                    is_python_script and PYTHON_PROCESS_CALL.search(line) is not None
                )
            if command_shaped:
                yield relative_path, line_number, line.lstrip().removeprefix("$ ")


def validate_risks(root, text_files, skill_text):
    findings = []
    disclosed = DISCLOSURE_PATTERN.search(skill_text) is not None
    severity = "Medium" if disclosed else "High"
    suffix = "; explicit permission is disclosed, but manual review remains" if disclosed else "; explicit permission is not disclosed"
    for relative_path, line_number, line in command_lines(root, text_files):
        for code, label, pattern in RISK_RULES:
            if pattern.search(line):
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
        skill_text = skill_file.read_text(encoding="utf-8")
        text_files = read_text_files(root)
        _, findings = validate_frontmatter(root, skill_text)
        findings.extend(validate_links(root, text_files))
        findings.extend(validate_placeholders(root, text_files))
        findings.extend(validate_risks(root, text_files, skill_text))
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
    parser = argparse.ArgumentParser(description=__doc__)
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
            atomic_write_text(options.output, content)
        else:
            sys.stdout.write(content)
        return 1 if document["status"] == "fail" else 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"validate_skill: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
