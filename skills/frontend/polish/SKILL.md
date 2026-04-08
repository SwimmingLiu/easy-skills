---
name: polish
description: "Performs a final quality pass on UI components before shipping — fixes pixel alignment, spacing inconsistencies, missing interaction states, transition smoothness, and visual detail issues in HTML/CSS/React artifacts. Use when the user asks to polish, finalize, do a last review of visual layouts, fix spacing or alignment, or refine UI details before shipping."
args:
  - name: target
    description: The feature or area to polish (optional)
    required: false
user-invokable: true
---

**First**: Use the frontend-design skill for design principles and anti-patterns.

Meticulous final pass to catch details that separate good work from great work. See [POLISH-CHECKLIST.md](POLISH-CHECKLIST.md) for the full dimension-by-dimension checklist.

## Pre-Polish Assessment

1. **Review completeness**: Is it functionally complete? What's the quality bar (MVP vs flagship)?
2. **Identify polish areas**: Visual inconsistencies, spacing/alignment, interaction state gaps, copy issues, edge cases, transition smoothness.

**CRITICAL**: Polish is the last step, not the first. Don't polish work that's not functionally complete.

## Polish Systematically

Work through each dimension. Key fixes with concrete examples:

### Spacing & Alignment
```css
/* Before: arbitrary values */
.card { margin: 13px 7px; padding: 11px; }

/* After: spacing scale */
.card { margin: var(--space-3) var(--space-2); padding: var(--space-3); }
```

### Transitions
```css
/* Before: no transition or wrong easing */
.button:hover { background: var(--primary-hover); }

/* After: smooth with natural deceleration */
.button {
  transition: background 200ms cubic-bezier(0.25, 1, 0.5, 1);
}
```

### Interaction States
Every interactive element needs all states. Missing states create broken experiences:
```css
.button { /* default */ }
.button:hover { /* subtle feedback */ }
.button:focus-visible { /* keyboard indicator - never remove */ }
.button:active { /* click feedback */ }
.button:disabled { /* clearly non-interactive */ }
.button[aria-busy="true"] { /* loading state */ }
```

### Color
- Tinted neutrals: no pure gray or pure black — add subtle color tint
- Never put gray text on colored backgrounds — use a shade of that color or transparency

### Key Values Reference
| Dimension | Target |
|-----------|--------|
| Transitions | 150-300ms, ease-out-quart/quint/expo |
| Touch targets | 44x44px minimum |
| Body line length | 45-75 characters |
| Mobile min text | 14px |
| Animation perf | Only transform + opacity, 60fps |

## Verify

For complete verification, work through every dimension in [POLISH-CHECKLIST.md](POLISH-CHECKLIST.md). Before marking done:

- Actually interact with the feature yourself
- Test at multiple viewport sizes
- Check all states (not just happy path)
- Ensure `prefers-reduced-motion` is respected
- Clean up: no console.logs, commented code, unused imports

**NEVER**:
- Polish before it's functionally complete
- Introduce bugs while polishing (test thoroughly)
- Perfect one thing while leaving others rough (consistent quality level)
