# CycloneDX JSON 1.7 Mapping Notes

Status: Draft
Owner: UNASSIGNED

## Purpose

CycloneDX JSON 1.7 is the leading first-exporter candidate because official JSON
schema validation can become an early contract test. This document does not
approve the exporter; it records what must be proven before approval.

## Mapping Principles

- Map from normalized evidence, not directly from filesystem collectors.
- Preserve whether a value is declared, observed, or derived.
- Use SHA-256 digests for selected model artifacts.
- Represent missing metadata as warnings, not fabricated BOM fields.
- Keep prompt, dataset, eval, and model-card contents out of generated summaries.

## Required Fixtures

- Complete model project.
- Sparse model project.
- Invalid config.
- Missing artifact.
- Secret redaction.
- Symlink escape.
- Exporter schema failure.

## Approval Criteria

- Generated CycloneDX JSON validates against the selected official schema.
- Golden fixtures are deterministic.
- Warning report and JSON summary stay consistent with the BOM output.
- Mapping docs identify any field that is declared rather than independently verified.

## Review Blockers

- The exporter reads files directly instead of consuming normalized evidence.
- The exporter implies legal license conclusions or compliance approval.
- The exporter passes schema validation but loses warning or source-location context.
