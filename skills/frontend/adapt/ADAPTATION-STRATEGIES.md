# Adaptation strategies reference

Detailed platform-specific adaptation strategies. Referenced from SKILL.md.

## Mobile Adaptation (Desktop → Mobile)

**Layout**: Single column, vertical stacking, full-width components, bottom navigation.

**Interaction**: Touch targets 44x44px minimum, swipe gestures where appropriate, bottom sheets instead of dropdowns, thumbs-first design (controls within thumb reach).

**Content**: Progressive disclosure (don't show everything at once), prioritize primary content, shorter text, 16px minimum font size.

**Navigation**: Hamburger menu or bottom navigation, reduce complexity, sticky headers, back button in flow.

## Tablet Adaptation (Hybrid)

**Layout**: Two-column layouts, side panels for secondary content, master-detail views, adaptive based on orientation.

**Interaction**: Support both touch and pointer, 44x44px targets but allow denser layouts than phone, side navigation drawers.

## Desktop Adaptation (Mobile → Desktop)

**Layout**: Multi-column layouts, side navigation always visible, multiple information panels simultaneously, fixed widths with max-width constraints.

**Interaction**: Hover states for additional information, keyboard shortcuts, right-click context menus, drag and drop, multi-select with Shift/Cmd.

**Content**: Show more information upfront, data tables with many columns, richer visualizations.

## Print Adaptation (Screen → Print)

**Layout**: Page breaks at logical points, remove navigation/footer/interactive elements, black and white or limited color, proper margins for binding.

**Content**: Expand shortened content (show full URLs, hidden sections), add page numbers/headers/footers, include metadata, convert charts to print-friendly versions.

## Email Adaptation (Web → Email)

**Layout**: 600px max width, single column only, inline CSS (no external stylesheets), table-based layouts for client compatibility.

**Interaction**: Large obvious CTAs (buttons not text links), no hover states, deep links to web app for complex interactions.
