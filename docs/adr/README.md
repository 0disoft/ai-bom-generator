# Architecture Decisions

Status: Draft
Owner: UNASSIGNED

## Purpose

This directory records durable architecture decisions for AI-BOM Generator.
Use ADRs when a choice affects the CLI contract, collector model, exporter
mapping, GitHub Action behavior, privacy stance, or validation strategy.

## Source of Truth

- Product decision: ADRs must keep implementation choices traceable to the evidence-first AI-BOM product boundary.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Boundary: Record decisions before expanding into hosted services, network access, dataset inspection, registry publishing, or compliance scoring.
- Data ownership: ADRs must name whether data is caller-owned input, normalized invocation evidence, or generated artifact.
- Failure and recovery behavior: ADRs must describe warning, failure, and compatibility behavior when public contracts change.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change makes a durable runtime, exporter, schema, or privacy decision only in code or examples.
- The change weakens the non-goal boundary without an ADR.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
