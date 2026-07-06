# Threat Model

Status: Draft

## Contract

Threat model covers untrusted local project paths, malicious metadata files,
large model artifacts, secret-bearing config, dependency manifests, GitHub
Action token scope, generated artifact disclosure, and misleading BOM claims.

## Required Evidence

- Source of truth: docs/data/privacy-and-retention.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change trusts caller-owned files without validation.
- A change follows symlinks, expands globs, or reads hidden paths without an explicit policy.
- A change makes compliance, license, safety, or vulnerability claims from incomplete evidence.
- A change copies prompt, dataset, eval, model-card, or model-weight contents into summaries by default.
- A change allows token-bearing URLs or credentialed Git remotes to pass into generated outputs unredacted.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
