# Public claim evidence map

| Claim | Evidence | Honest limit |
| --- | --- | --- |
| Four-page portfolio is publicly reachable | HTTPS smoke for `/`, `/design`, `/app`, `/privacy` | Does not prove final visual design |
| Public service fails closed with Provider disabled | API integration and container health tests | Does not prove live Provider quality |
| Runs are bounded by queue, budget and retention controls | API unit/integration tests and SQLite restart tests | Single-node only |
| QA and ticket product paths support two-stage generation | Offline live-target product fixtures and prior fixed synthetic runs | Stage 12 not run |
| Executable facts bind to sources and visible obligations | Selected public regressions and mechanical validators | Human semantic review still required |
| Human approval does not execute external actions | Decision API contract and absence of action adapters | Demonstration workflow only |
| Insufficient evidence can be shown as a typed pre-Provider handoff | `GEN-DEV-IE-001` replay asset, public expectation binding and Web tests | Verified replay only; inherited live chain does not yet enforce the same handoff |
| Public Beta can be rebuilt and rolled back | CI images, release manifest and controlled deployment rehearsal | No production HA/SLA |

No claim may be added to the homepage, resume or README without a code, test or runtime evidence row. Unknown or unrun claims remain `未验证`.
