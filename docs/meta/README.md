# Meta-development

Meta-development is the work of improving how agents develop this product: specification discipline, context structure, AgentOps, verification and rule evolution. It is a first-class learning asset, but it does not directly deliver product behavior.

## Boundary

- A meta increment needs a prior completion condition and must return to the product mainline.
- A one-off inconvenience becomes a note, not a rule. Generalize only repeated friction with observed evidence.
- Every retained governance change must be tested through a real product increment.
- Do not preserve raw chat, stdout, wire dumps, credentials or historical evidence trees as “learning”. Preserve normalized problem, decision, result and limitation.

## Record format

```text
real friction/failure
→ cause hypothesis
→ minimum governance change
→ product increment used to validate
→ observed effect
→ keep / revise / revert
```

Selected cases are under `case-studies/`; current rules live in `AGENTS.md` and `docs/engineering/`, not in case-study prose.

