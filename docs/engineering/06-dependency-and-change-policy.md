# Dependency and Change Policy

Status: Draft

## Contract

Dependency policy covers necessity, alternatives, license, maintenance health, vulnerabilities, runtime impact, bundle impact, major upgrade policy, and removal cost.

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
