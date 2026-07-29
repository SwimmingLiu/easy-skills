# Vault Record Contract

## Source

Required frontmatter: `id`, `type: source`, `status`, `source_type`, `source_url`, `author`, `published`, `captured`, `created`, `updated`, `sensitivity`, and `content_hash`.

The `## Preserved Content` section is immutable. Corrections and processing history belong under `## Processing Notes` as dated append-only entries.

## Derived knowledge

Concepts, decisions, people, organizations, and evidence records require stable `id`, `type`, `status`, `created`, `updated`, `confidence`, and one or more source wikilinks when they contain factual claims.

Recommended body sections are Current Synthesis, Evidence, Contradictions, Open Questions, and Related.

## Sensitivity

- `public`: safe to publish.
- `internal`: ordinary private working knowledge; default.
- `private`: personal or confidential material requiring deliberate sharing.
- `secret`: credentials or similarly sensitive values; never persist in this Git vault.
