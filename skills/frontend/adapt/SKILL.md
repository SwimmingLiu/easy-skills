---
name: adapt
description: "Creates responsive layouts and adapts UI for different screen sizes, devices, and platforms — generates media queries, adjusts breakpoints, converts fixed layouts to fluid grids, and optimizes touch targets. Use when the user asks for responsive design, mobile layout, breakpoint adjustments, viewport adaptation, cross-platform UI, or print/email styling."
args:
  - name: target
    description: The feature or component to adapt (optional)
    required: false
  - name: context
    description: What to adapt for (mobile, tablet, desktop, print, email, etc.)
    required: false
user-invokable: true
---

Adapt existing designs to work effectively across different contexts — screen sizes, devices, platforms, or use cases. See [ADAPTATION-STRATEGIES.md](ADAPTATION-STRATEGIES.md) for detailed platform-specific strategies.

## Assess Adaptation Challenge

1. **Identify the source context**: What was it designed for? What assumptions were made (screen size, input method, connection speed)?

2. **Understand target context**:
   - Device: mobile, tablet, desktop, TV, print, email?
   - Input: touch, mouse, keyboard, voice?
   - Usage: on-the-go vs desk, quick glance vs focused reading?

3. **Identify challenges**: What won't fit? What won't work (hover on touch, tiny targets)? What's inappropriate for the platform?

**CRITICAL**: Adaptation is not just scaling — it's rethinking the experience for the new context.

## Plan Strategy

Choose content-driven breakpoints where the design breaks, not arbitrary device sizes. Common defaults:

| Context | Width | Key Constraint |
|---------|-------|----------------|
| Mobile | 320-767px | Touch, single column, 44px targets |
| Tablet | 768-1023px | Touch + pointer, two columns |
| Desktop | 1024px+ | Hover, multi-column, keyboard shortcuts |

For platform-specific strategies (mobile, tablet, desktop, print, email), see [ADAPTATION-STRATEGIES.md](ADAPTATION-STRATEGIES.md).

## Implement

### Layout Adaptation
```css
/* Fluid grid with container queries */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
  gap: var(--space-4);
}

/* Fluid sizing */
.heading {
  font-size: clamp(1.25rem, 2vw + 1rem, 2rem);
}
```

### Touch Adaptation
```css
/* Ensure touch targets */
.interactive {
  min-height: 44px;
  min-width: 44px;
  padding: var(--space-3);
}

/* Remove hover-dependent interactions on touch */
@media (hover: none) {
  .tooltip-on-hover { display: none; }
  .tap-alternative { display: block; }
}
```

### Responsive Images
```html
<picture>
  <source media="(min-width: 1024px)" srcset="large.webp">
  <source media="(min-width: 768px)" srcset="medium.webp">
  <img src="small.webp" alt="..." loading="lazy">
</picture>
```

### Navigation Adaptation
Transform complex nav to hamburger/drawer on mobile, bottom nav bar for mobile apps, persistent side navigation on desktop.

**NEVER**:
- Hide core functionality on mobile
- Use different information architecture across contexts
- Break platform expectations (mobile users expect mobile patterns)
- Forget landscape orientation on mobile/tablet
- Use generic breakpoints blindly when content-driven breakpoints are better
- Ignore touch on desktop (many desktop devices have touch)

## Verify

- **Real devices**: Test on actual phones, tablets, desktops (not just DevTools)
- **Orientations**: Portrait and landscape
- **Browsers**: Safari, Chrome, Firefox, Edge
- **Input methods**: Touch, mouse, keyboard
- **Edge cases**: 320px (smallest), 4K (largest), throttled network
