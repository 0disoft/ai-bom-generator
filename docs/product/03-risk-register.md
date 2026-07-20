# Risk Register

Status: Draft
Owner: UNASSIGNED

## Purpose

This document tracks risks that can make an AI-BOM look more authoritative than
the evidence behind it.

## Source of Truth

- Product decision: Prefer explicit warnings over implied completeness.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Current Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sparse metadata looks complete | Users may treat a partial BOM as audited provenance | Emit missing-metadata warnings and include completeness status in JSON output |
| Exporter mapping is wrong | Downstream tools reject or misread BOM output | Build fixture-based mapping tests before claiming exporter support |
| Dataset license or source is guessed | Legal and trust claims become misleading | Only report declared dataset metadata; never infer license approval |
| Large checkpoint hashing is slow | CLI becomes painful in CI | Define digest caching or explicit artifact selection before broad use |
| Large directory trees make artifact selection slow | Discovery can spend excessive time walking irrelevant directories before hashing | Use one top-down walk, prune subtrees excluded by every active pattern, and keep a visited-entry ceiling UNDECIDED until measured fixtures justify one |
| Secrets leak through config or paths | BOM output may expose private URLs or tokens | Redact known sensitive values and document non-secret input requirements |
| Unknown credential shapes bypass strict redaction | A generated artifact may expose a new or organization-specific token format | Treat redaction as best effort, reject secret-bearing evidence by policy, and review artifacts before sharing |
| Concurrent runs share one output destination | Backup and replacement operations can mix files from different generations | Acquire stable locks for every generated destination in canonical path order and verify the committed manifest before consumption |
| "All frameworks" scope creep | Maintainer load explodes | Start with explicit config and fixtures instead of framework autodiscovery |

## Required Decisions Before Release

- Warning taxonomy.
- Completeness status field.
- Secret redaction policy.
- Exporter conformance fixtures.
- Validation needed before merge: VALIDATION.md.

## Review Blockers

- A change reduces warnings to make output look cleaner.
- A change claims audit or compliance status without manual review.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
