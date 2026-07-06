# Operational Contract

Status: Draft

## Operational Contract

Operational work centers on local CLI reliability, GitHub Action behavior,
deterministic artifact generation, warning visibility, and release safety. There
is no hosted service, database, or tenant runtime in the current product scope.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: failing CLI/action contract validation, nondeterministic output, secret leakage, or misleading BOM claims block release.
- Remaining operational risk: exact release policy, owner rotation, and support targets remain UNDECIDED.
