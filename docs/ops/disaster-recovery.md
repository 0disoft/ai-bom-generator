# Disaster Recovery

Status: Draft

## Operational Contract

Disaster recovery applies to a bad release that generates invalid BOMs, leaks
private metadata, breaks CI usage, changes action permissions, or makes warnings
look like successful evidence.

## Owners

Ownership, support, retention, and recovery follow [maintainer policy](maintainer-policy.md).

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: no rollback path for a broken CLI/action release blocks publication.
Current support, retention, platform-enforcement limits, and recovery decisions
are maintained in [maintainer policy](maintainer-policy.md).
