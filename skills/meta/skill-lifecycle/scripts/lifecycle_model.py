"""Lifecycle schema, state graph, and deterministic history replay."""

import copy
from datetime import datetime, timezone


SCHEMA_VERSION = 1
MATURITY_STATES = {
    "researched", "draft", "reviewed", "evaluated", "release-ready", "active", "retired"
}
CONFIRMED_STATES = {"active", "retired"}
EXCEPTION_STATES = {"needs-input", "blocked"}
OPERATIONS = {"discover", "create", "review", "evaluate", "optimize", "maintain"}

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
        "draft", "reviewed", "evaluated", "release-ready", "needs-input", "blocked"
    },
    "needs-input": set(),
    "blocked": set(),
}
PERSISTENT_STATES = set(ALLOWED_TRANSITIONS)
RESUMABLE_STATES = PERSISTENT_STATES - EXCEPTION_STATES


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


def initialized_snapshot():
    return {"state": "intake", "resume_state": None, "gates": {}, "artifacts": []}


def is_positive_integer(value):
    return type(value) is int and value > 0


def require_nonempty_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise LifecycleError(f"{field} must be a non-empty string")


def validate_state_pair(state, resume_state, prefix=""):
    state_field = f"{prefix}state"
    resume_field = f"{prefix}resume_state"
    if not isinstance(state, str) or state not in PERSISTENT_STATES:
        raise LifecycleError(f"{state_field} must be a valid persistent lifecycle state")
    if state in EXCEPTION_STATES:
        if not isinstance(resume_state, str) or resume_state not in RESUMABLE_STATES:
            raise LifecycleError(
                f"{resume_field} must be a resumable persistent state while {state_field} is {state}"
            )
    elif resume_state is not None:
        raise LifecycleError(
            f"{resume_field} must be null unless {state_field} is needs-input or blocked"
        )


def validate_gates(value, field):
    if not isinstance(value, dict):
        raise LifecycleError(f"{field} must be an object")
    for name, status in value.items():
        require_nonempty_string(name, f"{field} gate name")
        require_nonempty_string(status, f"{field}.{name}")


def validate_string_list(value, field, allow_empty=True, unique=False):
    if not isinstance(value, list):
        raise LifecycleError(f"{field} must be a list")
    if not allow_empty and not value:
        raise LifecycleError(f"{field} must not be empty")
    for index, item in enumerate(value):
        require_nonempty_string(item, f"{field}[{index}]")
    if unique and len(value) != len(set(value)):
        raise LifecycleError(f"{field} must contain unique references")


def validate_snapshot(value, field):
    if not isinstance(value, dict):
        raise LifecycleError(f"{field} must be an object")
    required = {"state", "resume_state", "gates", "artifacts"}
    missing = sorted(required.difference(value))
    if missing:
        raise LifecycleError(f"{field} is missing fields: {', '.join(missing)}")
    validate_state_pair(value["state"], value["resume_state"], f"{field}.")
    validate_gates(value["gates"], f"{field}.gates")
    validate_string_list(value["artifacts"], f"{field}.artifacts", unique=True)


def validate_run(value, index, document_version):
    field = f"runs[{index}]"
    if not isinstance(value, dict):
        raise LifecycleError(f"{field} must be an object")
    required = {
        "run_id", "timestamp", "operation", "previous_state", "current_state",
        "evidence_refs", "decision", "confirmed", "version", "snapshot",
    }
    missing = sorted(required.difference(value))
    if missing:
        raise LifecycleError(f"{field} is missing fields: {', '.join(missing)}")
    require_nonempty_string(value["run_id"], f"{field}.run_id")
    require_nonempty_string(value["timestamp"], f"{field}.timestamp")
    require_nonempty_string(value["operation"], f"{field}.operation")
    if value["operation"] not in OPERATIONS | {"rollback"}:
        raise LifecycleError(f"{field}.operation is not recognized")
    for state_field in ("previous_state", "current_state"):
        state = value[state_field]
        if not isinstance(state, str) or state not in PERSISTENT_STATES:
            raise LifecycleError(f"{field}.{state_field} must be a persistent state")
    validate_string_list(value["evidence_refs"], f"{field}.evidence_refs")
    if not isinstance(value["decision"], str):
        raise LifecycleError(f"{field}.decision must be a string")
    if type(value["confirmed"]) is not bool:
        raise LifecycleError(f"{field}.confirmed must be a boolean")
    if not is_positive_integer(value["version"]):
        raise LifecycleError(f"{field}.version must be a positive integer")
    if value["version"] > document_version:
        raise LifecycleError(f"{field}.version cannot exceed document version")
    if "event" in value and (
        value["event"] != "rolled-back" or value["operation"] != "rollback"
    ):
        raise LifecycleError(
            f"{field}.event must be rolled-back and requires operation rollback"
        )
    if value["operation"] == "rollback" and value.get("event") != "rolled-back":
        raise LifecycleError(f"{field}.event must be rolled-back for operation rollback")
    if value["operation"] == "rollback":
        if "restored_version" not in value:
            raise LifecycleError(f"{field} is missing fields: restored_version")
        if not is_positive_integer(value["restored_version"]):
            raise LifecycleError(f"{field}.restored_version must be a positive integer")
        if value["restored_version"] >= value["version"]:
            raise LifecycleError(f"{field}.restored_version must name a prior version")
    elif "restored_version" in value:
        raise LifecycleError(f"{field}.restored_version is valid only for rollback")
    validate_snapshot(value["snapshot"], f"{field}.snapshot")


def validate_replayed_transition(previous_snapshot, run, field, snapshots_by_version):
    previous_state = previous_snapshot["state"]
    current_state = run["current_state"]
    current_snapshot = run["snapshot"]
    if run["operation"] == "rollback":
        if not run["evidence_refs"]:
            raise LifecycleError(f"{field}.evidence_refs is required for rollback")
        if not run["confirmed"]:
            raise LifecycleError(f"{field}.confirmed must be true for rollback")
        restored_snapshot = snapshots_by_version.get(run["restored_version"])
        if restored_snapshot is None:
            raise LifecycleError(f"{field}.restored_version does not identify a prior snapshot")
        if current_snapshot != restored_snapshot:
            raise LifecycleError(
                f"{field}.restored_version snapshot does not match restored metadata"
            )
        return
    if previous_state in EXCEPTION_STATES:
        expected_state = previous_snapshot["resume_state"]
        if current_state != expected_state:
            raise LifecycleError(f"{field} may resume only to preserved state {expected_state!r}")
        expected_resume_state = None
    else:
        if current_state not in ALLOWED_TRANSITIONS[previous_state]:
            raise LifecycleError(
                f"{field} transition {previous_state} -> {current_state} is not allowed"
            )
        expected_resume_state = previous_state if current_state in EXCEPTION_STATES else None
        if current_state in MATURITY_STATES and not run["evidence_refs"]:
            raise LifecycleError(f"{field}.evidence_refs is required for maturity transition")
    if current_state in CONFIRMED_STATES and not run["confirmed"]:
        raise LifecycleError(f"{field}.confirmed must be true for transition to {current_state}")
    if current_snapshot["resume_state"] != expected_resume_state:
        raise LifecycleError(f"{field}.snapshot.resume_state does not match transition semantics")


def validate_document(document):
    required = {
        "schema_version", "skill", "state", "resume_state", "version", "runs",
        "gates", "artifacts",
    }
    missing = sorted(required.difference(document))
    if missing:
        raise LifecycleError(f"lifecycle file is missing fields: {', '.join(missing)}")
    if type(document["schema_version"]) is not int:
        raise LifecycleError("schema_version must be integer 1")
    if document["schema_version"] != SCHEMA_VERSION:
        raise LifecycleError(
            f"unsupported schema_version {document['schema_version']}; expected {SCHEMA_VERSION}"
        )
    require_nonempty_string(document["skill"], "skill")
    validate_state_pair(document["state"], document["resume_state"])
    if not is_positive_integer(document["version"]):
        raise LifecycleError("version must be a positive integer")
    if not isinstance(document["runs"], list):
        raise LifecycleError("runs must be a list")
    validate_gates(document["gates"], "gates")
    validate_string_list(document["artifacts"], "artifacts", unique=True)
    seen_run_ids = set()
    previous_snapshot = initialized_snapshot()
    snapshots_by_version = {1: initialized_snapshot()}
    for index, run in enumerate(document["runs"]):
        field = f"runs[{index}]"
        validate_run(run, index, document["version"])
        if run["run_id"] in seen_run_ids:
            raise LifecycleError(f"runs[{index}].run_id must be unique")
        seen_run_ids.add(run["run_id"])
        expected_version = index + 2
        if run["version"] != expected_version:
            raise LifecycleError(
                f"runs[{index}].version must be {expected_version} for contiguous history"
            )
        if run["previous_state"] != previous_snapshot["state"]:
            raise LifecycleError(
                f"runs[{index}].previous_state must match the prior snapshot state {previous_snapshot['state']}"
            )
        if run["current_state"] != run["snapshot"]["state"]:
            raise LifecycleError(f"runs[{index}].snapshot.state must match current_state")
        validate_replayed_transition(previous_snapshot, run, field, snapshots_by_version)
        previous_snapshot = run["snapshot"]
        snapshots_by_version[run["version"]] = run["snapshot"]
    expected_version = len(document["runs"]) + 1
    if document["version"] != expected_version:
        raise LifecycleError(f"document version must be {expected_version} for its run history")
    if not document["runs"] and snapshot(document) != initialized_snapshot():
        raise LifecycleError("empty run history must contain exact initialized metadata")
    if document["runs"] and document["runs"][-1]["snapshot"] != snapshot(document):
        raise LifecycleError("final snapshot must match current lifecycle metadata")
