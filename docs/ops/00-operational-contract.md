# Operational Contract

Status: Maintained guide

## Operational Contract

Operational work centers on local CLI reliability, GitHub Action behavior,
deterministic artifact generation, warning visibility, and release safety. There
is no hosted service, database, or tenant runtime in the current product scope.

## Owners

Ownership, support, retention, and recovery follow [maintainer policy](maintainer-policy.md).

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: failing CLI/action contract validation, nondeterministic output, secret leakage, or misleading BOM claims block release.
Current support, retention, platform-enforcement limits, and recovery decisions
are maintained in [maintainer policy](maintainer-policy.md).
