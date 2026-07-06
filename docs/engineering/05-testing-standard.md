# Testing Standard

Status: Draft

## Contract

Testing standard defines merge-blocking expectations for unit, integration, contract, migration, smoke, docs, and regression evidence.

## Required Evidence

- Source of truth: VALIDATION.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change adds collector or exporter behavior without complete, sparse, and failure fixtures.
- A change changes CLI or action output without updating contract tests.
- A change claims standards compatibility without exporter validation evidence.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
