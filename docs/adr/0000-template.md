# ADR Template

Status: Draft
Owner: UNASSIGNED

## Purpose

Use this template for decisions that change the AI-BOM Generator contract.
Each ADR should describe the evidence, options, selected approach, rejected
alternatives, compatibility impact, and validation needed before release.

## Source of Truth

- Product decision: ADRs must tie decisions back to the local evidence collector and standards-backed BOM exporter scope.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/README.md

## Required Sections

- Context: what product, data, CLI, action, exporter, or privacy question forced the decision.
- Decision: the selected approach and the public contract it creates or changes.
- Alternatives: credible options considered and why they were rejected.
- Boundary: explicit non-goals preserved by the decision.
- Data ownership: caller input, normalized evidence, generated artifact, or no data impact.
- Failure and recovery behavior: warning/failure behavior and migration impact.
- Validation needed before merge: VALIDATION.md.

## Review Blockers

- The ADR claims standards compatibility without mapping examples or fixture evidence.
- The ADR introduces network access, dataset inspection, or compliance scoring without a privacy and risk decision.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
