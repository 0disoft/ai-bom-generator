# Secrets

Status: Draft

## Operational Contract

MVP should not require secrets. Secret handling still matters because caller
projects, config files, lockfiles, metadata files, Git remotes, and CI logs may
contain private values that must not be copied into summaries or artifacts by
default.

## Owners

Ownership, support, retention, and recovery follow [maintainer policy](maintainer-policy.md).

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: secret leakage in logs, JSON summaries, fixtures, or generated artifacts blocks release.
Current support, retention, platform-enforcement limits, and recovery decisions
are maintained in [maintainer policy](maintainer-policy.md).
