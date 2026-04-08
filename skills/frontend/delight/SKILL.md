---
name: delight
description: "Adds micro-interactions, hover effects, loading animations, success celebrations, easter eggs, and playful UI copy to web interfaces. Use when the user asks to add delight, polish interactions, make a UI more engaging, add animations, micro-interactions, confetti, loading personality, or easter eggs."
args:
  - name: target
    description: The feature or area to add delight to (optional)
    required: false
user-invokable: true
---

Add moments of joy and personality that transform functional interfaces into delightful experiences. See [TECHNIQUES.md](TECHNIQUES.md) for a detailed catalog of delight patterns with code examples.

## MANDATORY PREPARATION

### Context Gathering (Do This First)

You cannot do a great job without context: target audience (critical), desired use-cases (critical), brand personality (playful vs professional vs quirky vs elegant), and what's appropriate for the domain.

Attempt to gather these from the current thread or codebase.

1. If you infer from existing design and must guess, STOP and {{ask_instruction}} whether you got it right.
2. If confidence is medium or lower, {{ask_instruction}} clarifying questions first.

Do NOT proceed until you have answers. Delight that's wrong for the context is worse than no delight at all.

### Use frontend-design skill

Use the frontend-design skill for design principles and anti-patterns. Do NOT proceed until it has executed.

## Assess Delight Opportunities

1. **Find natural delight moments**: success states, empty states, loading states, achievements/milestones, hover/click interactions, error softening, easter eggs.

2. **Define delight strategy** based on brand:
   - **Subtle sophistication**: Refined micro-interactions (luxury brands)
   - **Playful personality**: Whimsical illustrations and copy (consumer apps)
   - **Helpful surprises**: Anticipating needs before users ask (productivity tools)
   - **Sensory richness**: Satisfying sounds, smooth animations (creative tools)

If any of these are unclear from the codebase, {{ask_instruction}}

**CRITICAL**: Delight should enhance usability, never obscure it. If users notice the delight more than accomplishing their goal, you've gone too far.

## Delight Principles

- **Delight amplifies, never blocks**: moments should be quick (< 1 second), never delay core functionality, always skippable
- **Surprise and discovery**: hide delightful details for users to discover, reward exploration, don't announce every moment
- **Appropriate to context**: celebrate success, empathize with errors, respect user's state, match brand personality
- **Compound over time**: vary responses (not same animation every time), reveal deeper layers with continued use

## Apply Delight

Reference [TECHNIQUES.md](TECHNIQUES.md) for implementation details on:
- Micro-interactions & animation (button delight, loading, success, hover)
- Personality in copy (error messages, empty states, tooltips)
- Satisfying interactions (drag-and-drop, toggles, forms, progress)
- Easter eggs and seasonal touches
- Sound design (when appropriate)
- Celebration moments (confetti, achievements, milestones)

**NEVER**:
- Delay core functionality for delight
- Force users through delightful moments (make skippable)
- Use delight to hide poor UX
- Sacrifice performance for delight
- Ignore accessibility (respect `prefers-reduced-motion`, provide alternatives)
- Make every interaction delightful (special moments should be special)

## Verify

- Do users smile? Still pleasant after 100th time?
- Can users opt out or skip? No jank or slowdown?
- Matches brand and context? Works with reduced motion and screen readers?
