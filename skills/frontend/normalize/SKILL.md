---
name: normalize
description: "Aligns UI components, colors, typography, and spacing with an existing design system. Replaces hard-coded values with design tokens, swaps custom implementations for design system equivalents, and standardizes patterns across a feature. Use when the user asks to normalize styles, align with a design system, fix design inconsistencies, apply design tokens, or standardize component usage."
args:
  - name: feature
    description: The page, route, or feature to normalize (optional)
    required: false
user-invokable: true
---

Analyze and redesign the feature to match the project's design system standards, aesthetics, and established patterns.

## Plan

Before making changes, deeply understand the context:

1. **Discover the design system**: Search for design system documentation, UI guidelines, component libraries, or style guides (grep for "design system", "ui guide", "style guide", etc.). Understand:
   - Core design principles and aesthetic direction
   - Component patterns and conventions
   - Design tokens (colors, typography, spacing)

   **CRITICAL**: If something isn't clear, ask. Don't guess at design system principles.

2. **Analyze the current feature**:
   - Where does it deviate from design system patterns?
   - Which inconsistencies are cosmetic vs. functional?
   - Root cause: missing tokens, one-off implementations, or conceptual misalignment?

3. **Create a normalization plan** with specific changes:
   - Components to replace with design system equivalents
   - Styles to convert from hard-coded values to design tokens
   - UX patterns to match established user flows

## Execute

Systematically address inconsistencies. Example before/after for each dimension:

### Typography
```css
/* Before: hard-coded */
h2 { font-size: 24px; font-weight: 600; line-height: 1.3; }

/* After: design tokens */
h2 { font-size: var(--text-xl); font-weight: var(--font-semibold); line-height: var(--leading-snug); }
```

### Color & Theme
```css
/* Before: one-off color */
.card { background: #f5f5f5; border: 1px solid #e0e0e0; }

/* After: semantic tokens */
.card { background: var(--surface-secondary); border: 1px solid var(--border-default); }
```

### Spacing & Layout
```css
/* Before: arbitrary values */
.section { padding: 13px 22px; margin-bottom: 18px; }

/* After: spacing scale */
.section { padding: var(--space-3) var(--space-5); margin-bottom: var(--space-4); }
```

### Components
Replace custom implementations with design system components. Ensure props and variants match established patterns.

### Other Dimensions
- **Motion & interaction**: Match animation timing and easing to other features
- **Responsive behavior**: Ensure breakpoints align with design system standards
- **Accessibility**: Verify contrast ratios, focus states, ARIA labels match requirements

**NEVER**:
- Create new one-off components when design system equivalents exist
- Hard-code values that should use design tokens
- Introduce new patterns that diverge from the design system
- Compromise accessibility for visual consistency

## Clean Up

After normalization:

1. **Consolidate**: Move any new shared components to the design system or shared UI path
2. **Remove orphans**: Delete unused implementations, styles, or files made obsolete
3. **Verify**: Lint, type-check, and test. Run `npx eslint --fix` and any project-specific checks. Ensure no regressions
4. **DRY check**: Look for duplication introduced during refactoring and consolidate
