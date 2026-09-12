# Dependency and Change Policy

Status: Accepted

## Contract

Dependency policy covers necessity, alternatives, license, maintenance health, vulnerabilities, runtime impact, bundle impact, major upgrade policy, and removal cost.

Declare compatible package ranges and retain the lockfile's exact resolutions.
A major range alone is not reproducibility: the lock and Action SHA identify the
bytes used in a particular build. Same-major updates are proposed automatically
and must pass CI; they are not silently merged. New-major updates are separate
PRs requiring compatibility review and an intentional supported-range decision.
Pre-1.0 minor updates can break compatibility and require the same care.

Dependabot owns root Python/uv manifests and GitHub Action references, including
same-major SHA refreshes with version comments. Group only minor/patch updates;
major updates remain separate. Renovate owns only explicitly annotated uv and Bun
tool-version fields through its custom regex manager. It does not scan Python
manifests, Action references, or synthetic fixture dependencies. Its new-major
tool proposals require dashboard approval; same-major proposals do not.

No bot may merge, publish, or promote a tag. Review actual dependency changes,
license/runtime implications, and the proposed commit's CI. Revert a bad update
with a new commit; publish a patch if released runtime behavior was affected.
Update PRs #20 and #25 remain separate from this policy change. A producer-version
fixture records historical evidence and must not be upgraded as an installed
dependency. Bot runtime behavior is confirmed from its next hosted run, not from
the presence of configuration alone.

## Required Evidence

- Source of truth: docs/product/02-spec.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A dependency is added before runtime and package manager choices are recorded.
- A dependency is used for standards mapping without license, maintenance, and conformance review.
- A dependency introduces network behavior, native binaries, or CI permission needs without an ADR.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
