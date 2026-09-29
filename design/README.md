# Web design direction

These mockups define the visual direction before implementation. They are product-design references rather than screenshots of the current application.

## Page set

1. [`01-landing-page.png`](mockups/01-landing-page.png) — product positioning, core actions, statistics, and curriculum preview
2. [`02-roadmap-explorer.png`](mockups/02-roadmap-explorer.png) — searchable curriculum lanes, dependency progress, and selected-concept inspector
3. [`03-concept-overview.png`](mockups/03-concept-overview.png) — concept mental model, outcomes, prerequisites, next step, and track progress
4. [`04-lesson-reader.png`](mockups/04-lesson-reader.png) — focused technical reading, section navigation, production callouts, and knowledge checks
5. [`05-hands-on-lab.png`](mockups/05-hands-on-lab.png) — guided task panel, code editor, tests, retrieval inspector, and terminal

## Shared design language

- **Shell:** near-black `#0D0E0C`
- **Reading canvas:** warm ivory `#F3F0E8`
- **Primary signal:** acid lime `#D8FF5F`
- **Typography:** editorial sans-serif for hierarchy, monospace for technical metadata and code
- **Density:** compact developer-tool navigation with generous reading whitespace
- **Shape:** restrained corner radii; avoid card-on-card nesting
- **Motion:** purposeful progress and dependency transitions; respect reduced-motion preferences
- **Accessibility:** strong contrast, visible focus, text labels alongside status color, keyboard-complete navigation

## Product principles expressed by the design

- The roadmap is the product's organizing surface, not a marketing afterthought.
- Concepts show prerequisites and outcomes before asking learners to start.
- Lessons distinguish durable mechanisms from production rules and failure modes.
- Labs make evidence visible through tests, traces, scores, and source IDs.
- Progress is informative but never gamified into noise.

## Implementation order

1. Extract tokens, typography, spacing, controls, and navigation into a small design system.
2. Implement the shared application shell and responsive navigation.
3. Build the roadmap explorer and concept inspector.
4. Add concept and lesson routes with real Markdown rendering.
5. Build the lab workspace progressively; begin with static code/test fixtures before adding execution infrastructure.
6. Validate desktop, tablet, mobile, keyboard, contrast, and reduced-motion behavior.

## Generation details

Generated on 2026-09-29 with the built-in image generation tool using the `ui-mockup` use case. The prompts specified a shippable desktop product UI, the shared palette and hierarchy above, exact page-specific copy, and constraints against glassmorphism, generic purple SaaS gradients, cyberpunk styling, device frames, and decorative clutter.
