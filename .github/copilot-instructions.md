# GitHub Copilot instructions

Follow the repository-wide guidance in `AGENTS.md`.

- This is a dependency-free static HTML/CSS/JavaScript application with Python validation and labs.
- Reuse `assets/app.js`, `assets/styles.css`, and `curriculum/concepts.json`; do not introduce duplicated page data.
- Preserve the current design language and accessible, responsive behavior.
- Curriculum additions require valid prerequisites, two measurable outcomes, an exercise, and maintained primary references.
- Do not suggest credentials or paid model access for core exercises.
- Generated code should pass `./run.sh check`.
- Follow `.ai/BRANCHING.md` and the Discover-to-Deliver gates in `.ai/PHASES.md`.
- Keep BYO credentials out of browser code and examples; use `docs/BYO_LLM_AND_GPU.md` for optional API/GPU labs.
