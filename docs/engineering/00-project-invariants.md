# Project Invariants

Status: Draft

## Contract

AI-BOM Generator must remain a local-first evidence collector and BOM exporter.
Every implementation, fixture, doc, config, and release change must preserve the
non-goal boundary around compliance approval, vulnerability scanning, dataset
auditing, hosted registry behavior, and model serving.

## Required Evidence

- Source of truth: docs/product/02-spec.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change treats generated BOM output as proof of complete provenance.
- A change mutates caller-owned project files in MVP.
- A change adds implicit network access or hosted behavior.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
