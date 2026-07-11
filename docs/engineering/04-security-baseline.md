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
- Automated static analysis: `.github/workflows/codeql.yml` uploads Python
  CodeQL results with repository-content read and security-event write
  permissions only.
- Dependency updates: `.github/dependabot.yml` proposes grouped weekly `uv`
  and GitHub Actions updates through reviewable pull requests without merge or
  release authority.

## Review Blockers

- A change logs credentials, private dataset contents, model weights, or full source files.
- A change lets sensitive key names such as token, secret, password,
  credential, authorization, or api_key reach generated output unredacted.
- A change enables network access, registry publication, PR comments, or artifact upload without an explicit contract.
- Action-managed downloads must remain limited to the pinned runtime and the
  action checkout's locked dependencies; caller project dependency resolution
  and evidence upload remain blocked.
- A change treats user-provided paths or config as trusted.
- A change follows symlinks or reads outside the target root without an explicit policy.
- A change adds hidden cache, telemetry, or background state without an ADR.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
