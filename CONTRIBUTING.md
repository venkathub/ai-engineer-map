# Contributing

## Add a concept

1. Add its metadata to `curriculum/concepts.json`.
2. Use stable, lowercase kebab-case IDs.
3. Reference only prerequisite IDs that already exist.
4. Add a lesson in `content/<track>/<concept-id>.md` before marking it `published`.
5. Add an exercise or explain why the lesson is conceptual-only.
6. Run `python3 scripts/validate_curriculum.py` and the unit tests.

## Evidence standard

Prefer official documentation, standards, original research papers, and maintained source repositories. Secondary explanations may supplement but should not replace primary evidence for technical claims.

## Exercise standard

Exercises must have a clear observable outcome. Prefer deterministic local fixtures and tests. If an external model is optional, provide a local or mocked default path and label expected cost or account requirements.

## Pull requests

Keep curriculum and code changes focused. Describe the learner outcome, list new prerequisites, and include commands used for verification.
