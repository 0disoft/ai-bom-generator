# Security Baseline

Status: Draft

## Contract

Security baseline covers path handling, config validation, artifact hashing,
secret redaction, output validation, dependency intake, GitHub Action permission
boundaries, and avoidance of implicit network access.

## Required Evidence

- Source of truth: docs/data/privacy-and-retention.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change logs credentials, private dataset contents, model weights, or full source files.
- A change enables network access, registry publication, PR comments, or artifact upload without an explicit contract.
- A change treats user-provided paths or config as trusted.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
