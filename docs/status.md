# Current development status

> This is the only current-state entry. It does not accumulate closed history.

| Field | Value |
| --- | --- |
| `state` | `migrating` |
| Updated | `2026-07-23` |
| Current outcome | Establish one public, sustainable canonical repository without losing product or meta-development capability |
| Active increment | Canonical repository governance migration |
| Complexity | Full; architecture, repository identity, public source and deployment pipeline change |
| Risk / maturity | Local work `R0`; GitHub/deployment checkpoints `R2`; product remains `S1 public Beta` |
| Active work | `docs/work/active/canonical-repository-migration/` |
| Current action | Build and validate the sibling clean-baseline candidate; legacy repo and live deployment remain unchanged |
| Blockers | None for local candidate; public remote, canonical path swap and production deployment require their later gates |
| Provider | Disabled; zero calls and zero Provider cost in this increment |
| Next checkpoint | Governance baseline, API/Web migration, CI and local candidate tests pass |

## Current product truth

- The public direction-B replay experience is live at <https://47.84.34.86/>.
- Health must remain `replay_only`; live Provider is outside this increment.
- `product/0.1.0` is not released; Stage 12 and final visual design remain future work.
- The legacy repository remains authoritative until candidate, fresh clone, remote and canonical-path acceptance pass.

## Authority

- Product facts: `PROJECT.md`
- Outcome route: `ROADMAP.md`
- Active specification and plan: `docs/work/active/canonical-repository-migration/`
- Engineering rules: `docs/engineering/`

