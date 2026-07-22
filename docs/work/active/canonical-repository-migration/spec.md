# Canonical repository governance migration specification

> Status: `active`  
> Complexity: full  
> Risk/maturity: local `R0`; remote/deploy `R2`; product remains `S1`

## User-visible result

One public repository becomes the only long-term development base. An interviewer can understand and run the project without seeing raw internal history, while a new development agent can recover the same product, safety and meta-development boundaries from the repository alone.

## In scope

- Clean Git baseline and layered monorepo structure.
- Current product/API behavior, standard Next Web and replay deployment.
- Product/evaluation dependency inversion.
- Eight sanitized regressions and five meta-development cases.
- Governance/public-safety CI, GHCR images and digest deployment.
- A real `GEN-DEV-IE-001` replay preset increment.

## Out of scope

- Stage 12, any Provider call or fee, live public Provider, `product/0.1.0`, final visual redesign, domain purchase or production HA.

## Reuse review

- Reuse the existing public API control plane, Stage 11 product contracts, six synthetic knowledge files, direction-B Web, Docker/Caddy topology and reviewed budget/retention semantics.
- Use standard Next self-hosting and GitHub Actions/GHCR rather than maintaining Sites/vinext or a custom registry.
- Add only thin package and deployment adapters; do not change retrieval/generation semantics.

## Completion gates

- Public-safety scan passes before any remote creation.
- Old/new behavior fixtures, public API, replay Web and container checks pass.
- Cold-start answers 10/10 from canonical files only.
- Fresh clone builds/tests/runs.
- The real small replay increment closes under the new protocol.
- Public remote and digest deployment pass; current service remains `replay_only` and Provider usage is zero.
- User accepts repository organization, development comfort and public replay before legacy deletion.

