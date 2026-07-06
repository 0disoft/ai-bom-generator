# Release

Status: Draft

## Operational Contract

Release policy must cover CLI package publishing, GitHub Action tag behavior,
documentation updates, exporter compatibility, fixture evidence, and how users
are told about warning or output contract changes.

Public release should wait until the repository has an Apache-2.0 LICENSE file,
security policy, complete and sparse fixtures, secret-redaction fixtures,
exporter validation, README non-goal language, and a rollback path for the
CLI/action contract.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: contract drift, missing fixture evidence, invalid exporter output, or action permission drift blocks release.
- Remaining operational risk: versioning scheme, package registry, action tag policy, and rollout cadence remain UNDECIDED.
