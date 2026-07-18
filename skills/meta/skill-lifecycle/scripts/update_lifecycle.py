#!/usr/bin/env python3
"""Create and update an evidence-backed Skill lifecycle state file."""

import argparse
import copy
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from lifecycle_common import atomic_write_json, deterministic_json, read_json


SCHEMA_VERSION = 1
MATURITY_STATES = {
    "researched",
    "draft",
    "reviewed",
    "evaluated",
    "release-ready",
    "active",
    "retired",
}
CONFIRMED_STATES = {"active", "retired"}
EXCEPTION_STATES = {"needs-input", "blocked"}
OPERATIONS = {"discover", "create", "review", "evaluate", "optimize", "maintain"}

# This adjacency map is intentionally explicit: adding a state does not make it
# reachable until its permitted source states are reviewed here.
ALLOWED_TRANSITIONS = {
    "intake": {"researched", "needs-input", "blocked"},
    "researched": {"draft", "changes-required", "needs-input", "blocked"},
    "draft": {"reviewed", "changes-required", "needs-input", "blocked"},
    "reviewed": {"evaluated", "changes-required", "needs-input", "blocked"},
    "evaluated": {"release-ready", "changes-required", "needs-input", "blocked"},
    "release-ready": {"active", "changes-required", "needs-input", "blocked"},
    "active": {"retired", "changes-required", "needs-input", "blocked"},
    "retired": {"needs-input", "blocked"},
    "changes-required": {
        "draft",
        "reviewed",
        "evaluated",
        "release-ready",
        "needs-input",
        "blocked",
    },
    "needs-input": set(),
    "blocked": set(),
    "rolled-back": {"needs-input", "blocked"},
}


class LifecycleError(ValueError):
    """An actionable lifecycle validation failure."""


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def snapshot(document):
    return {
        "state": document["state"],
        "resume_state": document.get("resume_state"),
        "gates": copy.deepcopy(document["gates"]),
        "artifacts": list(document["artifacts"]),
    }


def load_document(path):
    try:
        document = read_json(path)
    except FileNotFoundError as error:
        raise LifecycleError(f"lifecycle file does not exist: {path}") from error
    except (OSError, ValueError) as error:
        raise LifecycleError(f"cannot read lifecycle file {path}: {error}") from error
    required = {
        "schema_version",
        "skill",
        "state",
        "resume_state",
        "version",
        "runs",
        "gates",
        "artifacts",
    }
    missing = sorted(required.difference(document))
    if missing:
        raise LifecycleError(f"lifecycle file is missing fields: {', '.join(missing)}")
    if document["schema_version"] != SCHEMA_VERSION:
        raise LifecycleError(
            f"unsupported schema_version {document['schema_version']}; expected {SCHEMA_VERSION}"
        )
    if document["state"] not in ALLOWED_TRANSITIONS:
        raise LifecycleError(f"unknown current state: {document['state']}")
    return document


def parse_gates(values):
    gates = {}
    for value in values:
        if "=" not in value:
            raise LifecycleError(f"invalid gate {value!r}; expected NAME=STATUS")
        name, status = value.split("=", 1)
        if not name.strip() or not status.strip():
            raise LifecycleError(f"invalid gate {value!r}; name and status are required")
        gates[name.strip()] = status.strip()
    return gates


def clean_evidence_refs(values):
    references = [value.strip() for value in values]
    if any(not value for value in references):
        raise LifecycleError("evidence references must be non-empty")
    return references


def make_run(
    document,
    operation,
    previous_state,
    current_state,
    evidence_refs,
    decision,
    event=None,
):
    run = {
        "run_id": str(uuid.uuid4()),
        "timestamp": timestamp(),
        "operation": operation,
        "previous_state": previous_state,
        "current_state": current_state,
        "evidence_refs": list(evidence_refs),
        "decision": decision or "",
        "version": document["version"],
        "snapshot": snapshot(document),
    }
    if event is not None:
        run["event"] = event
    return run


def command_init(arguments):
    path = Path(arguments.file)
    if path.exists():
        raise LifecycleError(f"refusing to overwrite existing lifecycle file: {path}")
    if not arguments.skill.strip():
        raise LifecycleError("--skill must not be empty")
    document = {
        "schema_version": SCHEMA_VERSION,
        "skill": arguments.skill.strip(),
        "state": "intake",
        "resume_state": None,
        "version": 1,
        "runs": [],
        "gates": {},
        "artifacts": [],
    }
    atomic_write_json(path, document)


def validate_transition(document, target, evidence_refs, confirmed):
    current = document["state"]
    if target not in ALLOWED_TRANSITIONS:
        raise LifecycleError(f"unknown target state: {target}")

    if current in EXCEPTION_STATES:
        resume_state = document.get("resume_state")
        if target != resume_state:
            raise LifecycleError(
                f"{current} may resume only to preserved state {resume_state!r}, not {target!r}"
            )
        return

    if target not in ALLOWED_TRANSITIONS[current]:
        raise LifecycleError(f"transition {current} -> {target} is not allowed")
    if target in MATURITY_STATES and not evidence_refs:
        raise LifecycleError(f"transition to {target} requires at least one --evidence reference")
    if target in CONFIRMED_STATES and not confirmed:
        raise LifecycleError(f"transition to {target} requires explicit --confirm")


def command_transition(arguments):
    document = load_document(arguments.file)
    if arguments.operation not in OPERATIONS:
        raise LifecycleError(
            f"unknown operation {arguments.operation!r}; choose from {', '.join(sorted(OPERATIONS))}"
        )
    evidence_refs = clean_evidence_refs(arguments.evidence)
    validate_transition(document, arguments.to, evidence_refs, arguments.confirm)
    gates = parse_gates(arguments.gate)

    updated = copy.deepcopy(document)
    previous_state = updated["state"]
    if previous_state in EXCEPTION_STATES:
        updated["resume_state"] = None
    elif arguments.to in EXCEPTION_STATES:
        updated["resume_state"] = previous_state
    else:
        updated["resume_state"] = None
    updated["state"] = arguments.to
    updated["version"] += 1
    updated["gates"].update(gates)
    for artifact in arguments.artifact:
        if artifact not in updated["artifacts"]:
            updated["artifacts"].append(artifact)
    updated["runs"].append(
        make_run(
            updated,
            arguments.operation,
            previous_state,
            arguments.to,
            evidence_refs,
            arguments.decision,
        )
    )
    atomic_write_json(arguments.file, updated)


def snapshot_for_version(document, target_version):
    if target_version == 1:
        return {"state": "intake", "resume_state": None, "gates": {}, "artifacts": []}
    for run in document["runs"]:
        if run.get("version") == target_version and "snapshot" in run:
            return copy.deepcopy(run["snapshot"])
    raise LifecycleError(f"version {target_version} has no restorable lifecycle snapshot")


def command_rollback(arguments):
    document = load_document(arguments.file)
    if not arguments.confirm:
        raise LifecycleError("rollback requires explicit --confirm")
    evidence_ref = clean_evidence_refs([arguments.evidence])[0]
    if arguments.to_version < 1 or arguments.to_version >= document["version"]:
        raise LifecycleError(
            f"--to-version must be between 1 and {document['version'] - 1}"
        )

    restored = snapshot_for_version(document, arguments.to_version)
    updated = copy.deepcopy(document)
    previous_state = updated["state"]
    updated.update(restored)
    updated["version"] = document["version"] + 1
    updated["runs"].append(
        make_run(
            updated,
            "rollback",
            previous_state,
            updated["state"],
            [evidence_ref],
            f"restored lifecycle snapshot from version {arguments.to_version}",
            event="rolled-back",
        )
    )
    atomic_write_json(arguments.file, updated)


def command_show(arguments):
    sys.stdout.write(deterministic_json(load_document(arguments.file)))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Guard Skill lifecycle state transitions with evidence and history."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize lifecycle state")
    init_parser.add_argument("--file", required=True, help="lifecycle JSON path")
    init_parser.add_argument("--skill", required=True, help="Skill name")
    init_parser.set_defaults(handler=command_init)

    transition_parser = subparsers.add_parser(
        "transition", help="apply one guarded state transition"
    )
    transition_parser.add_argument("--file", required=True, help="lifecycle JSON path")
    transition_parser.add_argument("--to", required=True, help="target state")
    transition_parser.add_argument("--operation", required=True, help="lifecycle operation")
    transition_parser.add_argument(
        "--evidence", action="append", default=[], metavar="REF", help="evidence reference"
    )
    transition_parser.add_argument("--decision", help="decision or reason")
    transition_parser.add_argument(
        "--gate", action="append", default=[], metavar="NAME=STATUS", help="gate update"
    )
    transition_parser.add_argument(
        "--artifact", action="append", default=[], metavar="PATH", help="artifact path"
    )
    transition_parser.add_argument(
        "--confirm", action="store_true", help="confirm a side-effecting state change"
    )
    transition_parser.set_defaults(handler=command_transition)

    show_parser = subparsers.add_parser("show", help="print deterministic lifecycle JSON")
    show_parser.add_argument("--file", required=True, help="lifecycle JSON path")
    show_parser.set_defaults(handler=command_show)

    rollback_parser = subparsers.add_parser(
        "rollback", help="restore a prior lifecycle metadata snapshot"
    )
    rollback_parser.add_argument("--file", required=True, help="lifecycle JSON path")
    rollback_parser.add_argument("--to-version", required=True, type=int)
    rollback_parser.add_argument("--evidence", required=True, metavar="REF")
    rollback_parser.add_argument("--confirm", action="store_true")
    rollback_parser.set_defaults(handler=command_rollback)
    return parser


def main(argv=None):
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        arguments.handler(arguments)
    except LifecycleError as error:
        parser.exit(2, f"error: {error}\n")
    except OSError as error:
        parser.exit(2, f"error: filesystem operation failed: {error}\n")
    return 0


if __name__ == "__main__":
    main()
