# Incident Response

Status: Maintained guide

## Operational Contract

Incidents are release or documentation failures that can mislead users about
AI-BOM completeness, expose private input information, break CI pipelines, or
change generated output without a migration path.

## Owners

Ownership, support, retention, and recovery follow [maintainer policy](maintainer-policy.md).

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: unresolved secret disclosure, invalid exporter output, or action permission escalation blocks release.
- Vulnerability intake and disclosure path: GitHub Private Vulnerability
  Reporting and repository security advisories, as documented in `SECURITY.md`.
Current support, retention, platform-enforcement limits, and recovery decisions
are maintained in [maintainer policy](maintainer-policy.md).
