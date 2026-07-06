# Observability

Status: Draft

## Operational Contract

Observability means local terminal output, machine-readable JSON summaries,
warning reports, GitHub Action logs, and generated artifact metadata. There are
no dashboards, traces, or health checks unless a future hosted surface is
explicitly added.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: warnings or failures missing from JSON/action logs block release.
- Remaining operational risk: log redaction rules and long-term artifact retention remain UNDECIDED.
