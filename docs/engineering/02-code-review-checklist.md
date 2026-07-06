# Code Review Checklist

Status: Draft

## Contract

Code review blockers include ownership drift, hidden auth or tenant rules, untested failure paths, contract drift, fake validation success, and generated-output dependency.

## Required Evidence

- Source of truth: docs/product/02-spec.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change changes CLI, action, collector, exporter, or warning behavior without updating the matching contract doc.
- A change accepts untrusted paths, config, or artifacts without validation.
- A change embeds private source contents in logs, summaries, fixtures, or generated output.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
