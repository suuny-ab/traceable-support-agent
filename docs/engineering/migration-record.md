# Canonical migration record

This record identifies the private source baselines and the allowlist used to create the clean public history. It intentionally contains no private archive location, machine path, Provider output, credential, request header or consumed HOLDOUT text.

## Source identity

- Product baseline: `ab2c4b8a374937a8727e414991799dba490db30b`
- Direction-B Web baseline: `b1bcc94c5cf122a6c6dcff5d007eb6194d47dcc7`
- New history starts from an allowlist reconstruction; none of the old 385 commits are ancestors of this repository.

## Inclusion rule

Included: current product contracts, public control plane, synthetic knowledge, eight redacted regression expectations, direction-B Web source, current governance, reproducible deployment files and public-safe migration hashes.

Excluded: old evidence and numbered audit areas, non-selected specifications/plans, consumed HOLDOUT material, Provider originals, execution envelopes, logs, SQLite state, archives, caches, build output, model binaries, credentials and machine-specific paths.

## Synthetic knowledge inventory

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `after-sales-policy.md` | 2047 | `0c30193d1dffec7ab37690883197e7e4314338f7bf2526a2ce3ffef3abe94d2e` |
| `common-faq.md` | 1890 | `06da5e5366603822d75cd090e4a797b2dc8e3cd49badf35f57082516fc363377` |
| `customer-service-sop.json` | 2545 | `373f813469c6f088bfcca9702ae8904a1bf962a16430f77b85bb4a5ed7e2c554` |
| `fault-codes.json` | 2746 | `1f8f8d1c675f7143d85a536cf89e79c2a993c31329fa67cd67391b88068885a8` |
| `manual-cz-r1.md` | 2120 | `076504c08e6ce81a001469a0bddc3bebae8620e9785fc30f5b58e276e0e3b06c` |
| `manual-cz-r2.md` | 2149 | `5a54c630d70716fba68d4ac988ecf1910a7ec655726adbef154528c7d26a84a8` |

The canonical six-file inventory hash is `41948be4be64f6e1aeb49db7a5be30c5b5570b8dbbf7ee6c1bfa74bddf0f3303`; the parsed 27-unit inventory hash is `714538ce5b649f3acf566ac53f93dc9201f6a80d13430c7e3e293436d7e55161`.

## Runtime equivalence

`evals/migration-equivalence-v1.json` freezes API, prompt, Provider and knowledge identities. `evals/fixtures/migration-retrieval-equivalence-v1.json` contains only ordered unit IDs, logical document/section identifiers and text hashes. The fixture generated from the old and new packages is byte-identical with SHA-256 `81c9a483f541a452c49d4d6f5bbae26582b95c27b829d5f35c81f4afdd335ef7`.

This proves extraction equivalence for the frozen cases; it does not prove Stage 12 quality or release `product/0.1.0`.
