# Contributing

## Add a concept

1. Add its metadata to `curriculum/concepts.json`.
2. Use stable, lowercase kebab-case IDs.
3. Reference only prerequisite IDs that already exist.
4. Provide at least two observable learning outcomes and a proof-of-understanding exercise.
5. Add the concept to a track with maintained primary references; add a topic-specific reference when the track sources are not sufficient.
6. Keep dependency relationships acyclic and update the curriculum review date only after verifying affected claims.
7. Run `python3 scripts/validate_curriculum.py` and the unit tests.

Exercises must begin with an observable action and must be unique. They are rendered as Inspect, Modify, or Build work in the lab. A completion artifact needs real evidence for both outcomes, source/version provenance, one failure case, and one production trade-off; the browser checklist alone is not proof of completion.

## Evidence standard

Prefer official documentation, standards, original research papers, and maintained source repositories. Secondary explanations may supplement but should not replace primary evidence for technical claims.

## Exercise standard

Exercises must have a clear observable outcome. Prefer deterministic local fixtures and tests. If an external model is optional, provide a local or mocked default path and label expected cost or account requirements.

## Pull requests

Keep curriculum and code changes focused. Describe the learner outcome, list new prerequisites, and include commands used for verification.
