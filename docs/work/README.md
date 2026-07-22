# Work records

Standard and full increments live in `active/<slug>/` with four small files:

- `spec.md`: user-visible outcome, scope, risk/maturity and acceptance;
- `plan.md`: ordered implementation and stop conditions;
- `result.md`: observed delivery and verification, never intended claims;
- `review.md`: independent fixed-snapshot findings and closure.

There is exactly one user-facing active increment. Once its code, verification, review and fact updates are closed, move the entire directory to `completed/`; completed work cannot authorize new changes. Lightweight work needs only a concise result in the affected current document and a bounded commit.

Git records technical closure. GitHub publication, production deployment, user acceptance and destructive cleanup remain separate checkpoints and cannot be inferred from a tracked file.

