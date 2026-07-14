# Data Lineage

Status: Draft
Owner: UNASSIGNED

## Purpose

Lineage records where each BOM field came from and whether the value was declared,
derived, or missing.

## Source of Truth

- Product decision: Every collected field must keep source context.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Lineage Fields

- Source file path or config path.
- Source field name when structured.
- Collection mode: declared, derived, defaulted, or missing.
- Lockfile package index or requirements-file line for parsed dependency
  packages, plus directly evidenced package source fields such as a conda-lock
  platform, matched channel, Poetry source or resolved Git revision, remote
  locator, and artifact hashes.
- Digest algorithm and value for hashed artifacts.
- Warning code when metadata is absent or ambiguous.

## Boundary

Lineage is for generated BOM explainability. It does not prove that the source
metadata is true, complete, licensed, or safe.

## Validation Needed Before Merge

- Fixtures must assert source paths and warning codes, not only final exported values.

## Review Blockers

- The change emits BOM fields without traceable source context.
- The change converts missing metadata into silent defaults.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
