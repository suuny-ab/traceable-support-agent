# Case: HOLDOUT identity and recovery

> Evidence level: `legacy-summary`. No HOLDOUT content, raw log or custody package is published; this summary is not independently reproducible after legacy deletion.

## Friction

Mechanism retries were described as new dataset versions, and long formal work risked either repeating verified work or losing custody semantics after interruption.

## Hypothesis and change

Freeze semantic content separately from execution attempts. Record `content_identity`, `content_version`, `attempt_id`, `last_verified_checkpoint`, resume preconditions, restart scope and hard-stop classes.

## Validation

The formal HOLDOUT flow could distinguish a fixed suite from recovery attempts and resume only when bytes, hashes, bindings and prior logs remained unchanged.

## Result

Keep for formal work only. Sealing/custody does not prove candidate quality; a revealed HOLDOUT is regression-only.
