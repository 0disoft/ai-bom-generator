# Secrets

Status: Draft

## Operational Contract

MVP should not require secrets. Secret handling still matters because caller
projects, config files, lockfiles, metadata files, Git remotes, and CI logs may
contain private values that must not be copied into summaries or artifacts by
default.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: secret leakage in logs, JSON summaries, fixtures, or generated artifacts blocks release.
- Remaining operational risk: explicit redaction taxonomy and future token-backed integrations remain UNDECIDED.
