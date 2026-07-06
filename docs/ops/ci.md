# CI

Status: Draft

## Operational Contract

CI must prove the CLI/action contract with docs checks, fixture tests, exporter
validation once an exporter is selected, deterministic output checks, and
permission review for the GitHub Action wrapper.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: failing check/test/docs validation, nondeterministic fixture output, or action permission drift blocks release.
- Remaining operational risk: exact branch protection and hosted CI matrix remain UNDECIDED.
