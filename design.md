# Design — Stratify

A locked design system for this app. Every page redesign reads this file before emitting code. Do not regenerate per page — extend or amend this file when the system needs to grow.

## Genre
modern-minimal (Austerity Monochrome variant)

## Macrostructure family
- Marketing/Main pages: Bento Grid (`01-bento-grid`)
- Analytical/Operational pages: Workbench (`05-workbench`) / Tabular Console
- Interaction pages: Chat Panel / Dialog Panel

## Theme (Professional Monochrome)
- `--color-paper`      oklch(99.2% 0.001 250) /* Crisp off-white background */
- `--color-paper-2`    oklch(97.5% 0.002 250) /* Elevation 1 surface / light panels */
- `--color-paper-3`    oklch(95.0% 0.003 250) /* Elevation 2 surface / card hover */
- `--color-ink`        oklch(15.0% 0.004 250) /* Deep carbon-black primary text */
- `--color-ink-2`      oklch(40.0% 0.005 250) /* Slate gray secondary text */
- `--color-rule`       oklch(85.0% 0.003 250) /* Thin light hairline borders (increased contrast) */
- `--color-rule-2`     oklch(89.0% 0.002 250) /* Subtler dividers (increased contrast) */
- `--color-muted`      oklch(55.0% 0.004 250) /* Muted labels */
- `--color-neutral`    oklch(45.0% 0.004 250) /* Medium grey details */
- `--color-accent`     oklch(18.0% 0.004 250) /* Pitch black accent highlights */
- `--color-accent-ink` oklch(99.0% 0.001 250) /* Text overlay on accent background (white on black) */
- `--color-focus`      oklch(50.0% 0.005 250) /* Focus ring */

### Dark Mode Overrides (`[data-theme="dark"]`)
- `--color-paper`      oklch(10.0% 0.002 250) /* Pitch carbon black */
- `--color-paper-2`    oklch(14.0% 0.003 250) /* Deep charcoal surface */
- `--color-paper-3`    oklch(18.0% 0.004 250) /* Slightly lighter charcoal for card hover */
- `--color-ink`        oklch(99.0% 0.001 250) /* Crisp, premium off-white text */
- `--color-ink-2`      oklch(78.0% 0.002 250) /* Soft slate text (increased contrast) */
- `--color-rule`       oklch(35.0% 0.004 250) /* Clearly visible borders in dark mode */
- `--color-rule-2`     oklch(25.0% 0.003 250) /* Subtler dividers in dark mode */
- `--color-muted`      oklch(65.0% 0.002 250) /* Muted gray labels (increased contrast) */
- `--color-neutral`    oklch(68.0% 0.002 250) /* Medium grey details (increased contrast) */
- `--color-accent`     oklch(99.2% 0.001 250) /* Crisp white accent highlights */
- `--color-accent-ink` oklch(10.0% 0.002 250) /* Dark text overlay on accent */
- `--color-accent-dim`  oklch(99.2% 0.001 250 / 0.08)

/* Semantic status mappings (muted desaturated tones for professional look) */
- `--color-success`    oklch(62.0% 0.06 145)  /* Muted Sage Green */
- `--color-warning`    oklch(68.0% 0.06 75)   /* Muted Ochre Amber */
- `--color-error`      oklch(55.0% 0.07 25)   /* Muted Terracotta Red */
- `--color-info`       oklch(58.0% 0.06 195)  /* Muted Slate Blue */

## Typography
- Display: Plus Jakarta Sans, weight 500/700, style normal
- Body:    Geist, weight 300 / 400 / 500 / 600
- Mono:    JetBrains Mono, weight 400 / 600
- Display tracking: -0.02em
- Type scale anchor: --text-display = clamp(1.5rem, 3vw + 0.5rem, 2.75rem)

## Spacing
4-point named scale. Pages must use named tokens, never raw pixel values:
- `--space-3xs`: 0.25rem;  /* 4px */
- `--space-2xs`: 0.5rem;   /* 8px */
- `--space-xs`:  0.75rem;  /* 12px */
- `--space-sm`:  1rem;     /* 16px */
- `--space-md`:  1.5rem;    /* 24px */
- `--space-lg`:  2rem;     /* 32px */
- `--space-xl`:  3rem;     /* 48px */
- `--space-2xl`: 4.5rem;   /* 72px */
- `--space-3xl`: 7rem;     /* 112px */

## Motion
- Easings:
  - `--ease-out`: cubic-bezier(0.16, 1, 0.3, 1) (elements entering)
  - `--ease-in`: cubic-bezier(0.7, 0, 0.84, 0) (elements leaving)
  - `--ease-in-out`: cubic-bezier(0.65, 0, 0.35, 1) (state toggles)
- Durations:
  - `--dur-micro`: 120ms
  - `--dur-short`: 220ms
  - `--dur-long`:  420ms
- Reveal pattern: Smooth fade-in and subtle translate-up page animations when switching views.

## Microinteractions stance
- Hover is smooth and responsive, utilizing cards lifting/translating slightly (`translateY(-2px)`) and background surface shift.
- Buttons invert colors on hover (solid black becomes white outline with black text).
- Active nav tab uses a solid black accent vertical line on the left.

## CTA voice
- Primary CTA: Solid black background, white text. Inverts to outline state on hover.
- Secondary CTA: Outlined with rule, text in black.

## Exports

### tokens.css
```css
:root {
  --color-paper:      oklch(99.2% 0.001 250);
  --color-paper-2:    oklch(97.5% 0.002 250);
  --color-paper-3:    oklch(95.0% 0.003 250);
  --color-ink:        oklch(15.0% 0.004 250);
  --color-ink-2:      oklch(40.0% 0.005 250);
  --color-rule:       oklch(85.0% 0.003 250);
  --color-rule-2:     oklch(89.0% 0.002 250);
  --color-muted:      oklch(55.0% 0.004 250);
  --color-neutral:    oklch(45.0% 0.004 250);
  --color-accent:     oklch(18.0% 0.004 250);
  --color-accent-ink: oklch(99.0% 0.001 250);
  --color-focus:      oklch(50.0% 0.005 250);

  /* Status Colors */
  --color-success:    oklch(62.0% 0.06 145);
  --color-warning:    oklch(68.0% 0.06 75);
  --color-error:      oklch(55.0% 0.07 25);
  --color-info:       oklch(58.0% 0.06 195);
  
  /* Dim status colors for alert/tag backgrounds */
  --color-success-dim: oklch(62.0% 0.06 145 / 0.08);
  --color-warning-dim: oklch(68.0% 0.06 75 / 0.08);
  --color-error-dim:   oklch(55.0% 0.07 25 / 0.08);
  --color-info-dim:    oklch(58.0% 0.06 195 / 0.08);
  --color-accent-dim:  oklch(18.0% 0.004 250 / 0.06);

  --font-display:     "Plus Jakarta Sans", sans-serif;
  --font-body:        "Geist", sans-serif;
  --font-mono:        "JetBrains Mono", monospace;

  --space-3xs: 0.25rem;
  --space-2xs: 0.5rem;
  --space-xs:  0.75rem;
  --space-sm:  1rem;
  --space-md:  1.5rem;
  --space-lg:  2rem;
  --space-xl:  3rem;
  --space-2xl: 4.5rem;
  --space-3xl: 7rem;

  --text-xs:   0.75rem;
  --text-sm:   0.875rem;
  --text-base: 1rem;
  --text-md:   1.125rem;
  --text-lg:   1.25rem;
  --text-xl:   1.5rem;
  --text-2xl:  1.875rem;
  --text-display: clamp(1.5rem, 3vw + 0.5rem, 2.75rem);

  --ease-out:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in:   cubic-bezier(0.7, 0, 0.84, 0);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --dur-micro: 120ms;
  --dur-short: 220ms;
  --dur-long:  420ms;
  
  --radius-card: 8px;
  --radius-button: 6px;
  --radius-input: 6px;
}

[data-theme="dark"] {
  --color-paper:      oklch(10.0% 0.002 250);
  --color-paper-2:    oklch(14.0% 0.003 250);
  --color-paper-3:    oklch(18.0% 0.004 250);
  --color-ink:        oklch(99.0% 0.001 250);
  --color-ink-2:      oklch(78.0% 0.002 250);
  --color-rule:       oklch(35.0% 0.004 250);
  --color-rule-2:     oklch(25.0% 0.003 250);
  --color-muted:      oklch(65.0% 0.002 250);
  --color-neutral:    oklch(68.0% 0.002 250);
  --color-accent:     oklch(99.2% 0.001 250);
  --color-accent-ink: oklch(10.0% 0.002 250);
  --color-accent-dim:  oklch(99.2% 0.001 250 / 0.08);
}
```
