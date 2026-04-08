# Delight techniques reference

Detailed catalog of delight techniques for UI/UX. Referenced from SKILL.md.

## Micro-interactions & Animation

**Button delight**:
```css
.button {
  transition: transform 0.1s, box-shadow 0.1s;
}
.button:active {
  transform: translateY(2px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.button:hover {
  transform: translateY(-2px);
  transition: transform 0.2s cubic-bezier(0.25, 1, 0.5, 1);
}
```

**Loading delight**: Playful loading animations, personality in loading messages, progress indication with encouraging messages, skeleton screens with subtle animations.

**Success animations**: Checkmark draw animation, confetti burst for major achievements, gentle scale + fade for confirmation.

**Hover surprises**: Icons that animate on hover, color shifts or glow effects, tooltip reveals with personality, custom cursors for branded experiences.

## Personality in Copy

**Playful error messages**:
```
"Error 404" → "This page is playing hide and seek. (And winning)"
"Connection failed" → "Looks like the internet took a coffee break. Want to retry?"
```

**Encouraging empty states**:
```
"No projects" → "Your canvas awaits. Create something amazing."
"No messages" → "Inbox zero! You're crushing it today."
```

Match copy personality to brand. Banks shouldn't be wacky, but they can be warm.

## Illustrations & Visual Personality

- Custom illustrations for empty, error, loading, success states (not stock icons)
- Animated icons with subtle motion on hover/click
- Background effects: subtle particles, gradient mesh, geometric patterns, parallax depth, time-of-day themes

## Satisfying Interactions

- **Drag and drop**: Lift effect on drag, snap animation when dropped, undo toast
- **Toggle switches**: Smooth slide with spring physics, color transition, haptic feedback
- **Progress & achievements**: Streak counters, progress bars that celebrate at 100%, badge unlocks
- **Form interactions**: Input fields animate on focus, checkboxes bounce when checked, auto-grow textareas

## Sound Design

Subtle audio cues when appropriate: notification sounds, success sounds, error sounds, typing sounds. Always respect system sound settings, provide mute option, keep volumes quiet.

## Easter Eggs & Hidden Delights

- Konami code unlocks special theme
- Hidden keyboard shortcuts
- Hover reveals on logos or illustrations
- Console messages for developers
- Seasonal touches: holiday themes, weather-based variations, time-based changes
- Randomized variations (not same every time)

## Loading & Waiting States

Interesting loading messages that rotate, progress bars with personality, mini-games during long loads, fun facts or tips while waiting.

```
Example rotation:
- "Waking up the servers..."
- "Teaching robots to dance..."
- "Consulting the magic 8-ball..."
```

## Celebration Moments

- Confetti for major milestones
- Animated checkmarks for completions
- "Achievement unlocked" style notifications
- Personalized messages ("You published your 10th article!")
- First-time actions get special treatment, streak tracking, anniversary celebrations

## Implementation Libraries

- **Animation**: Framer Motion (React), GSAP (universal), Lottie (After Effects), Canvas confetti
- **Sound**: Howler.js, use-sound (React hook)
- **Physics**: React Spring, Popmotion

File size matters. Compress images, optimize animations, lazy load delight features.
