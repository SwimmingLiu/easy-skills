# Polish checklist reference

Detailed polish dimensions for final quality pass. Referenced from SKILL.md.

## Visual Alignment & Spacing

- Pixel-perfect alignment to grid at all breakpoints
- Consistent spacing using spacing scale (no random 13px gaps)
- Optical alignment: adjust for visual weight (icons may need offset for optical centering)
- Enable grid overlay and verify alignment
- Check spacing with browser inspector

## Typography Refinement

- Hierarchy consistency: same elements use same sizes/weights throughout
- Line length: 45-75 characters for body text
- Line height: appropriate for font size and context
- Widows & orphans: no single words on last line
- Kerning: adjust letter spacing where needed (especially headlines)
- Font loading: no FOUT/FOIT flashes

## Color & Contrast

- All text meets WCAG contrast standards
- No hard-coded colors, all use design tokens
- Works in all theme variants
- Tinted neutrals: no pure gray or pure black — add subtle color tint (0.01 chroma)
- Never put gray text on colored backgrounds — use a shade of that color or transparency

## Interaction States

Every interactive element needs: default, hover, focus (keyboard indicator), active, disabled, loading, error, success.

## Micro-interactions & Transitions

- All state changes animated 150-300ms
- Use ease-out-quart/quint/expo for natural deceleration (never bounce or elastic)
- 60fps: only animate transform and opacity
- Respect `prefers-reduced-motion`

## Content & Copy

- Consistent terminology and capitalization
- No typos, appropriate length
- Punctuation consistency (periods on sentences, not on labels)

## Icons & Images

- Consistent icon family and sizing
- Proper optical alignment with adjacent text
- All images have descriptive alt text
- No layout shift on load, proper aspect ratios
- 2x assets for retina

## Forms & Inputs

- All inputs properly labeled
- Clear and consistent required indicators
- Helpful, consistent error messages
- Logical tab order
- Consistent validation timing (on blur vs on submit)

## Edge Cases

- All async actions have loading feedback
- Helpful empty states, not blank space
- Clear error messages with recovery paths
- Handles very long content and missing data gracefully

## Responsiveness

- Test mobile (320px+), tablet (768px+), desktop (1024px+)
- Touch targets 44x44px minimum on touch devices
- No text smaller than 14px on mobile
- No horizontal scroll

## Performance

- Optimize critical path
- No layout shift (CLS)
- Smooth 60fps interactions
- Responsive images with lazy loading
