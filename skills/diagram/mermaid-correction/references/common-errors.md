# Common Mermaid Validator Errors

Use these patterns when diagnosing Mermaid parse failures from `scripts/validate-mermaid.mjs`.

## Typical Failure Categories

### Invalid connectors

- Flowcharts require connectors such as `-->`, `---`, `-.->`, `==>`.
- Sequence diagrams require message syntax such as `A->>B: message`.
- ERDs require Mermaid relationship tokens like `||--o{`.

### Wrong diagram header

Examples:

- `flowchart TD`
- `sequenceDiagram`
- `classDiagram`
- `erDiagram`
- `stateDiagram-v2`

If the header is malformed, the parser often fails on line 1.

### Unsupported punctuation or stray prose

- Extra colons, braces, or commas in the wrong place
- Natural-language sentences mixed into the diagram body
- Broken code fences accidentally copied into the Mermaid body

### Broken node or participant declarations

- Flowchart nodes should follow Mermaid node syntax such as `A[Label]` or `B{Decision}`.
- Sequence participants should be declared as `participant API` or implied by message lines.

## Diagnosis Heuristics

1. Trust the reported line first.
2. Use `error.expecting` and `error.got` to identify the malformed token class.
3. Rewrite the full block if the current layout is inconsistent or mixed with prose.
4. Re-run validation after every rewrite. Never rely on visual inspection alone.
