# Evidence And Lifecycle Contract

The lifecycle file is an audit log for one Skill. It records decisions and lifecycle metadata; it does not copy, rewrite, or restore arbitrary Skill files.

## Document schema

Schema version 1 is a UTF-8 JSON object with these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Must be `1`. |
| `skill` | string | Stable Skill name supplied at initialization. |
| `state` | string | Current persistent lifecycle state. Event vocabulary is never stored here. |
| `resume_state` | string or null | Persistent state preserved while work is in `needs-input` or `blocked`; null otherwise. |
| `version` | integer | Monotonically increasing successful mutation number; initialization is version 1. |
| `runs` | array | Ordered transition and rollback audit records. |
| `gates` | object | Gate name to status mappings, updated by explicit `NAME=STATUS` arguments. |
| `artifacts` | array | Unique artifact path references in first-recorded order. |

Initialization creates state `intake`, version 1, a null `resume_state`, and empty `runs`, `gates`, and `artifacts`.

Each successful transition appends a run with a unique `run_id`, UTC `timestamp`, `operation`, `previous_state`, `current_state`, `evidence_refs`, `decision`, boolean `confirmed`, and resulting `version`. `confirmed` defaults to false and records whether explicit confirmation was supplied. Runs also carry a lifecycle metadata `snapshot` used by guarded rollback. A rollback run has operation `rollback` and event `rolled-back`.

The loader validates the complete parseable document before showing or mutating it. `schema_version` must be integer 1 and `version` must be a positive integer; JSON booleans do not satisfy either integer field. `skill` must be a non-empty string. `runs` and `artifacts` must be arrays, `gates` must be an object with non-empty string names and statuses, and artifact entries must be unique non-empty strings. Every run must be an object with the fields above using their documented scalar or array types, a unique `run_id`, and a required `snapshot`. Each snapshot contains a valid persistent `state`, valid `resume_state`, gates object, and unique artifacts array.

Mutation run versions are unique, strictly increasing, and contiguous from 2. An empty run history must contain the exact initialized metadata: version 1, `intake`, null `resume_state`, and empty gates and artifacts. Otherwise, the document `version` equals the last run version. Each normal run is replayed against the explicit transition table, including exact exception-state resume behavior, maturity evidence, and confirmation for `active` and `retired`. Its `previous_state` matches the preceding snapshot state, its `current_state` matches its own snapshot state, and the final snapshot matches current lifecycle metadata. These invariants ensure every version accepted by rollback has exactly one restorable snapshot. Malformed but parseable documents are rejected with an actionable validation error rather than partially processed.

Evidence references are non-empty path or identifier strings. They point to durable inputs such as inventories, review reports, evaluation results, owner decisions, or retirement analysis. The engine records references; it does not interpret or verify the referenced content.

## State vocabulary

- Normal maturity states: `intake`, `researched`, `draft`, `reviewed`, `evaluated`, `release-ready`, `active`, and `retired`.
- Revision state: `changes-required`.
- Exception states: `needs-input` and `blocked`.
- Rollback event vocabulary: `rolled-back`. This is an audit event only, never a persistent `state`, `resume_state`, or snapshot state.

The engine uses this explicit transition contract:

| From | Allowed targets |
| --- | --- |
| `intake` | `researched`, `needs-input`, `blocked` |
| `researched` | `draft`, `changes-required`, `needs-input`, `blocked` |
| `draft` | `reviewed`, `changes-required`, `needs-input`, `blocked` |
| `reviewed` | `evaluated`, `changes-required`, `needs-input`, `blocked` |
| `evaluated` | `release-ready`, `changes-required`, `needs-input`, `blocked` |
| `release-ready` | `active`, `changes-required`, `needs-input`, `blocked` |
| `active` | `retired`, `changes-required`, `needs-input`, `blocked` |
| `retired` | `needs-input`, `blocked` |
| `changes-required` | `draft`, `reviewed`, `evaluated`, `release-ready`, `needs-input`, `blocked` |

Entering `needs-input` or `blocked` preserves the source state in `resume_state`. The only allowed exit is back to that exact preserved state, after which `resume_state` is cleared. This prevents exception handling from bypassing maturity gates.

## Guards

Entering `researched`, `draft`, `reviewed`, `evaluated`, `release-ready`, `active`, or `retired` requires at least one evidence reference. Resuming from an exception state is not a new maturity transition and uses the existing evidence history. Entering `active` or `retired` additionally requires explicit confirmation.

Validation completes before mutation. Illegal transitions, malformed gates, missing evidence, missing confirmation, unreadable documents, and unsupported schema versions return a nonzero exit with an actionable error on stderr. Failed commands leave the lifecycle file byte-identical.

## Atomic writes and rollback boundary

Every mutation serializes deterministic JSON to a temporary file next to the destination, flushes it, and installs it with `os.replace`. Keeping the temporary file on the same filesystem provides atomic replacement semantics.

Mutations hold a stable sibling interprocess lock across load, validation, mutation, and atomic replacement; initialization holds the same lock across its existence check and creation. Platforms without `fcntl.flock` fail explicitly rather than running unlocked. Lifecycle paths that are symlinks, including dangling symlinks, are rejected for every command. After replacement on POSIX, the containing directory is synchronized so the directory entry is durable.

Rollback requires a prior version, one evidence reference, and explicit confirmation recorded as `confirmed: true`. It restores only the prior lifecycle snapshot: `state`, `resume_state`, `gates`, and `artifacts`. It retains the audit history, increments the current version, and appends a run whose `event` is `rolled-back` and whose `restored_version` identifies the exact earlier snapshot. The run's `previous_state` and `current_state` remain persistent states; `current_state` is the restored snapshot state. Replay verifies the evidence, confirmation, and exact match between the rollback snapshot and `restored_version`; rollback is the only run exempt from normal transition adjacency. It never changes `SKILL.md`, references, scripts, assets, evaluation data, or any other arbitrary file. Restoring artifact contents belongs to a version-control or backup workflow outside this tool.

## CLI

```text
update_lifecycle.py init --file PATH --skill NAME
update_lifecycle.py transition --file PATH --to STATE --operation OP [--evidence REF ...] [--decision TEXT] [--gate NAME=STATUS ...] [--artifact PATH ...] [--confirm]
update_lifecycle.py show --file PATH
update_lifecycle.py rollback --file PATH --to-version N --evidence REF --confirm
```
