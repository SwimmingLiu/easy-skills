# Maintain

## Goal

Inventory managed Skills, detect drift and overlap, and decide **Keep**, **Improve**, **Update**, **Merge**, or **Retire** from reproducible evidence.

## Inputs

- Require approved roots, target hosts, registry or prior inventory, support policy, and maintenance cadence.
- For each Skill, require or mark unknown its source, ref, path, content hash, license, host compatibility, version, dependencies, and owner.
- Gather evaluation, safety, compatibility, replacement, and usage evidence without equating missing telemetry with non-use.

## Procedure

1. Run `inventory_skills.py` and discover strictly named `SKILL.md` files. Ignore arbitrary Markdown, caches, generated copies, and unsupported roots.
2. Compare current source/ref/path/hash with the registry. Classify local modifications, upstream changes, missing sources, dependency drift, host drift, and license changes.
3. Run scheduled smoke checks; run full review, evaluation, and security gates for critical, changed, or high-risk Skills.
4. Distinguish discovered, loaded, triggered, completed, accepted, and rolled-back usage when evidence exists. Mark usage unknown when it does not; mtime and read counts are weak signals only.
5. Choose `Keep` when current and supported, `Improve` for verified local quality gaps, `Update` for reviewed upstream changes, `Merge` for redundant capabilities with a safe migration, or `Retire` for confirmed replacement, obsolescence, or unacceptable risk.
6. For Update, Merge, or Retire, list dependents, affected hosts, migration steps, replacement, archive, release notes, and rollback path.
7. Re-inventory after confirmed changes and record new hashes, versions, gates, and decisions.

## Outputs

- Produce deterministic JSON and Markdown inventory, drift findings, smoke or full-check results, and one recommendation per Skill.
- For Merge or Retire, produce dependency, replacement, migration, archive, and rollback records.

## State transition

Keep a passing Skill `active`. Route verified deficiencies to `changes-required` and `optimize`. Move to `retired` only after the retirement gate is confirmed and migration evidence is recorded. Preserve retired evidence and identity rather than deleting history.

## Human gate

Keep inventory and comparison read-only. Ask the user to confirm before fetching or installing updates, overwriting local modifications, merging packages, changing dependencies, archiving, deleting, publishing, or retiring. Confirm network and paid checks separately.

## Design basis

- Apply ECC `skill-stocktake` Quick/Full scope and Keep/Improve/Update/Merge/Retire decision vocabulary.
- Apply Vercel Skills CLI source/ref/path/hash tracking for reproducible identity and update comparison.
- Apply Agent Skills package identity and host-aware compatibility checks.
- Reject stocktake's weak usage inference: never retire from mtime, a single read log, or absent telemetry alone.
