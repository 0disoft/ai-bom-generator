# Config and Environment

Status: Draft

## Operational Contract

Configuration controls model directory selection, explicit metadata references,
artifact include/exclude patterns, exporter format, output paths, and warning
policy. Secrets are not required for MVP and environment-variable behavior is
not a default contract.

Explicit MVP config files use `aibom.toml` and AI-BOM config schema v1. The CLI
validates schema version, section shape, artifact pattern types, warning-policy
values, and known path fields before writing output files. Explicit CLI flags
override config values. The CLI does not perform implicit config discovery and
does not read environment variables for config in MVP.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: invalid config accepted as valid, secret-bearing config logged, or CLI/action config precedence drift blocks release.
- Remaining operational risk: automatic config discovery, environment-variable config policy, GitHub Action config compatibility, and compatibility policy remain UNDECIDED.
