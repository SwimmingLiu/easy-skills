---
name: mermaid-correction
description: Validate, diagnose, and repair Mermaid code blocks with an iterative check → correct → re-check workflow. Use when Mermaid diagrams fail to render, contain parse errors, need syntax validation before commit, or when a user asks to fix, debug, lint, validate, or rewrite Mermaid flowcharts, sequence diagrams, ERDs, class diagrams, state diagrams, C4 diagrams, gantt charts, git graphs, or other Mermaid syntax.
---

# Mermaid Correction

Validate Mermaid syntax with the official Mermaid CLI, explain the exact parse failure, rewrite the full Mermaid block, and loop until the diagram passes validation or three attempts are exhausted.

## Script Directory

Scripts live in `scripts/`. `${SKILL_DIR}` = this skill directory. Use Node.js from the current environment. Run commands from `${SKILL_DIR}/scripts` so local dependencies resolve correctly.

| Script | Purpose |
|--------|---------|
| `scripts/validate-mermaid.mjs` | Validate Mermaid with Mermaid CLI and emit structured JSON success/error output |

## Validation Command

Install dependencies once inside `${SKILL_DIR}/scripts` if `node_modules/` is missing:

```bash
npm install
```

Then validate Mermaid from a file:

```bash
node "${SKILL_DIR}/scripts/validate-mermaid.mjs" --file /absolute/path/to/diagram.mmd
```

Or validate inline Mermaid by piping stdin:

```bash
cat <<'EOF' | node "${SKILL_DIR}/scripts/validate-mermaid.mjs"
flowchart TD
    A --> B
EOF
```

Exit code `0` means valid Mermaid. Exit code `1` means invalid Mermaid or invalid invocation.

The validator uses the official `@mermaid-js/mermaid-cli` backend, so successful validation means Mermaid can actually render the diagram, not just partially parse it.

Expect a small cold-start delay on first run because Mermaid CLI launches headless Chromium through Puppeteer.

## Workflow

Follow this workflow exactly. Do not skip validation.

### Step 1: Materialize the Mermaid Block

1. If the user provided a fenced code block, strip the outer fences and validate only the Mermaid body.
2. Preserve the original diagram type, labels, comments, and indentation unless a syntax fix requires a change.
3. If the input mixes prose with Mermaid, isolate only the Mermaid code before validation.

### Step 2: First Check

Run the validator script and inspect its JSON output.

- If `valid` is `true`, return the Mermaid as already valid and stop.
- If `valid` is `false`, capture these fields when present:
  - `error.message`
  - `error.line`
  - `error.column`
  - `error.excerpt`
  - `error.expecting`
  - `error.got`

### Step 3: Diagnose the Syntax Problem

Explain the failure in plain language before rewriting. Focus on the concrete parse error, for example:

- invalid arrow syntax in flowcharts
- misplaced participant/message syntax in sequence diagrams
- malformed entity or cardinality markers in ERDs
- unsupported tokens, stray punctuation, or missing line breaks
- wrong diagram header such as `graph`/`flowchart`/`sequenceDiagram`

If the syntax family is unclear, consult `../mermaid-diagrams/SKILL.md` and the matching reference file in `../mermaid-diagrams/references/`.

## Correction Loop

You have **at most 3 validation attempts total**.

### Attempt 1

1. Validate the original Mermaid.
2. If invalid, explain the parse error.
3. Rewrite the **entire Mermaid block**, not just the failing line.

### Attempt 2

1. Validate the rewritten Mermaid.
2. If still invalid, explain the new parse error.
3. Rewrite the full Mermaid block again.

### Attempt 3

1. Validate the second rewrite.
2. If valid, return the corrected Mermaid.
3. If still invalid, return:
   - the latest Mermaid block,
   - the final validator error,
   - a short note that the 3-attempt limit was reached.

Never claim Mermaid is fixed without a passing validation result.

## Output Format

Use this structure unless the user asked for a different format:

```markdown
## Check Result
- Status: valid | invalid
- Attempt: N/3
- Diagram type: <type if known>
- Error: <message or "none">

## Diagnosis
<plain-language explanation of the syntax issue>

## Corrected Mermaid
```mermaid
<full rewritten Mermaid block>
```

## Re-check Result
- Status: valid | invalid
- Attempt: N/3
- Error: <message or "none">
```

If the first validation passes, omit the correction section and simply report that the Mermaid is already valid.

## Guardrails

- Keep the semantic meaning of the diagram intact while fixing syntax.
- Do not silently change the diagram type unless the original header is clearly invalid and the intended type is obvious from the content.
- Prefer minimal semantic change and maximal syntax clarity.
- Preserve comments beginning with `%%` when possible.
- Do not stop after diagnosis; always attempt a rewrite if validation fails.
- Do not exceed 3 validation attempts.

## References

- Mermaid authoring guidance: `../mermaid-diagrams/SKILL.md`
- Syntax reference examples: `../mermaid-diagrams/references/`
- Common validator output patterns: `references/common-errors.md`
