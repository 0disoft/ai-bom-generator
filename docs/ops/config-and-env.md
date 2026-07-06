# Config and Environment

Status: Draft

## Operational Contract

Configuration controls model directory selection, explicit metadata references,
artifact include/exclude patterns, exporter format, output paths, and warning
policy. Secrets are not required for MVP and environment-variable behavior is
not a default contract.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: invalid config accepted as valid, secret-bearing config logged, or CLI/action config precedence drift blocks release.
- Remaining operational risk: config filename, schema, environment variable policy, and compatibility policy remain UNDECIDED.
