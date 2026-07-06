# Disaster Recovery

Status: Draft

## Operational Contract

Disaster recovery applies to a bad release that generates invalid BOMs, leaks
private metadata, breaks CI usage, changes action permissions, or makes warnings
look like successful evidence.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: no rollback path for a broken CLI/action release blocks publication.
- Remaining operational risk: maintainer escalation path and registry-specific yank/deprecate policy remain UNDECIDED.
