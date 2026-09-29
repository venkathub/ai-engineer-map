# Contributing

## Add a concept

1. Add its metadata to `curriculum/concepts.json`.
2. Use stable, lowercase kebab-case IDs.
3. Reference only prerequisite IDs that already exist.
4. Provide at least two observable learning outcomes and a proof-of-understanding exercise.
5. Add the concept to a track with maintained primary references; add a topic-specific reference when the track sources are not sufficient.
6. Keep dependency relationships acyclic and update the curriculum review date only after verifying affected claims.
7. Run `python3 scripts/validate_curriculum.py` and the unit tests.

Every concept ID must also appear in `curriculum/hoe.json`. Assign `guided-browser` until an executable profile is genuinely available; do not label setup instructions as automated. Automated profiles require both shell-free `run` and `verify` argv arrays.

Exercises must begin with an observable action and must be unique. They are rendered as Inspect, Modify, or Build work in the lab. A completion artifact needs real evidence for both outcomes, source/version provenance, one failure case, and one production trade-off; the browser checklist alone is not proof of completion.

## Author a tutorial

Authored tutorials are mapped in `content/tutorials.json`. Use a local Markdown path under `content/rag/` for the current RAG path and a working Python baseline under `labs/`. Add the topic once to the ordered path and point `verifyTest` to its behavioral unittest class. Extend the content path convention and validator explicitly when adding another track.

Each tutorial needs these sections: Why it matters, Mental model, Worked example, Guided experiment, Production trade-offs and failure cases, Independent challenge, Knowledge check, and References. Include at least 250 words of developed, topic-specific material, expected observations, runnable commands, and its actual technical-review date. Length is only a validation floor, not an editorial quality guarantee. The lesson reader adds curriculum prerequisites and path navigation. The supported Markdown subset is headings, paragraphs, unordered lists, fenced code, inline code, and links; raw HTML is escaped.

Only add a tutorial mapping when the corresponding HOE profile runs the declared baseline with that topic ID and verifies it with the declared test class. Until then, the lesson must remain visibly labeled as an outline. Run `./run.sh check` and the optional reader browser regression. Do not replace a model, ANN index, or parser with a toy surrogate without stating that limitation.

## Source evidence

Prefer official documentation, standards, original research papers, and maintained source repositories. Secondary explanations may supplement but should not replace primary evidence for technical claims.

## Exercise standard

Exercises must have a clear observable outcome. Prefer deterministic local fixtures and tests. If an external model is optional, provide a local or mocked default path and label expected cost or account requirements.

Use `./run.sh hoe inspect CONCEPT_ID` to review the resolved mode, status, commands, artifacts, and cleanup. API and GPU profiles stay `setup-ready` until they have an explicit cost acknowledgement and topic-specific verification; repository automation must never provision them.

## Pull requests

Keep curriculum and code changes focused. Describe the learner outcome, list new prerequisites, and include commands used for verification.

Every non-draft PR receives a read-only Claude review. Address every actionable finding and push the correction; each push invalidates the previous result and triggers a complete re-review. Merge only after `claude-review` reports `APPROVED` with zero findings and all required checks pass. See [`docs/CLAUDE_PR_REVIEW.md`](docs/CLAUDE_PR_REVIEW.md).
