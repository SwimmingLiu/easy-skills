# Evidence And Lifecycle Contract

The lifecycle file is an audit log for one Skill. It records decisions and lifecycle metadata; it does not copy, rewrite, or restore arbitrary Skill files.

## Document schema

Schema version 1 is a UTF-8 JSON object with these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Must be `1`. |
| `skill` | string | Stable Skill name supplied at initialization. |
| `state` | string | Current lifecycle state. |
| `resume_state` | string or null | State preserved while work is in `needs-input` or `blocked`. |
| `version` | integer | Monotonically increasing successful mutation number; initialization is version 1. |
| `runs` | array | Ordered transition and rollback audit records. |
| `gates` | object | Gate name to status mappings, updated by explicit `NAME=STATUS` arguments. |
| `artifacts` | array | Unique artifact path references in first-recorded order. |

Initialization creates state `intake`, version 1, a null `resume_state`, and empty `runs`, `gates`, and `artifacts`.

Each successful transition appends a run with a unique `run_id`, UTC `timestamp`, `operation`, `previous_state`, `current_state`, `evidence_refs`, `decision`, and resulting `version`. Runs also carry a lifecycle metadata `snapshot` used by guarded rollback. A rollback run has operation `rollback` and event `rolled-back`.

Evidence references are non-empty path or identifier strings. They point to durable inputs such as inventories, review reports, evaluation results, owner decisions, or retirement analysis. The engine records references; it does not interpret or verify the referenced content.

## State vocabulary

- Normal maturity states: `intake`, `researched`, `draft`, `reviewed`, `evaluated`, `release-ready`, `active`, and `retired`.
- Revision state: `changes-required`.
- Exception states: `needs-input` and `blocked`.
- Rollback event vocabulary: `rolled-back`.

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

Rollback requires a prior version, one evidence reference, and explicit confirmation. It restores only the prior lifecycle snapshot: `state`, `resume_state`, `gates`, and `artifacts`. It retains the audit history, increments the current version, and appends a `rolled-back` event. It never changes `SKILL.md`, references, scripts, assets, evaluation data, or any other arbitrary file. Restoring artifact contents belongs to a version-control or backup workflow outside this tool.

## CLI

```text
update_lifecycle.py init --file PATH --skill NAME
update_lifecycle.py transition --file PATH --to STATE --operation OP [--evidence REF ...] [--decision TEXT] [--gate NAME=STATUS ...] [--artifact PATH ...] [--confirm]
update_lifecycle.py show --file PATH
update_lifecycle.py rollback --file PATH --to-version N --evidence REF --confirm
```
