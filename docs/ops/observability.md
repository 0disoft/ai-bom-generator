# Observability

Status: Maintained guide

## Operational Contract

Observability means local terminal output, machine-readable JSON summaries,
warning reports, GitHub Action logs, and generated artifact metadata. There are
no dashboards, traces, or health checks unless a future hosted surface is
explicitly added.

## Owners

Ownership, support, retention, and recovery follow [maintainer policy](maintainer-policy.md).

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: warnings or failures missing from JSON/action logs block release.
Current support, retention, platform-enforcement limits, and recovery decisions
are maintained in [maintainer policy](maintainer-policy.md).
