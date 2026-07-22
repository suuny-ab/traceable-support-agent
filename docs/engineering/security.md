# Security and privacy engineering

## Threat model

Public anonymous callers are untrusted. The service defends against accidental or hostile oversized input, Origin abuse, predictable identifiers, queue/budget exhaustion, sensitive/out-of-scope input, cross-run binding mistakes, HTML injection, raw-content logging and false success states.

The service does not claim to defend against an administrator with arbitrary server or repository write access. Host, GitHub and cloud-account security remain platform responsibilities.

## Controls

- HTTPS through Caddy; exact Origin allowlist and no wildcard CORS.
- Maximum 16 KiB HTTP body and maximum 500 Chinese characters of user content.
- Cryptographically random run IDs; no user history/list endpoint.
- Maximum 2 running and 4 queued jobs.
- Per-browser soft limit and atomic global daily/monthly budget reservation.
- Sensitive, safety and scope preflight before any Provider construction.
- Zero automatic Provider retry; key never appears in request parameters, logs, SQLite or error responses.
- No raw request or Provider response logging.
- HTML output is escaped/rendered as text; stable public error codes omit tracebacks and local paths.
- Approval records a human decision only and performs no external business action.

## Live readiness

Live mode requires all of: explicit environment switch, assembled live runner, installed and verified dependencies/model, credential presence, passing budget/privacy gates and health readiness. A credential alone never changes health to live.

## Repository safety

CI rejects credentials, local home paths, archives, databases, large files and private evaluation material. Actions are pinned to full commit SHAs. Production secrets exist only in GitHub Environment secrets and server environment files with restricted permissions.

