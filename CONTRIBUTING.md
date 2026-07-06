# Contributing

Status: Draft
Owner: UNASSIGNED

## Purpose

This document defines how contributors should change AI-BOM Generator without
turning it into a model registry, compliance oracle, vulnerability scanner, or
hosted governance service.

## Source of Truth

- Product decision: Contributions must preserve the evidence-first AI/ML BOM generator boundary.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Boundary: Changes may add collectors, exporters, fixtures, docs, or CLI/action contract updates; they must not add hosted services or automatic legal/security conclusions.
- Data ownership: Input model-project files belong to the caller; generated BOMs and warning reports are derived artifacts.
- Failure and recovery behavior: Missing metadata should produce warnings; invalid config, unreadable required inputs, hash failures, and exporter failures should fail with actionable context.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change claims compliance, safety, vulnerability, or license conclusions that the tool cannot prove.
- The change adds implicit network access, registry publication, or dataset-content inspection without a product decision.
- The change invents exporter mappings without fixtures or standard-backed evidence.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
