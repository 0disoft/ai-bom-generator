# CycloneDX JSON 1.7 Mapping Notes

Status: Draft
Owner: UNASSIGNED

## Purpose

CycloneDX JSON 1.7 is the first implemented exporter because official JSON
schema validation can become an early contract test. This document records the
mapping constraints that must stay true as the exporter matures.

## Mapping Principles

- Map from normalized evidence, not directly from filesystem collectors.
- Preserve whether a value is declared, observed, or derived.
- Use SHA-256 digests for selected model artifacts.
- Represent missing metadata as warnings, not fabricated BOM fields.
- Keep prompt, dataset, eval, and model-card contents out of generated summaries.
- Map collected local Git HEAD/ref/commit evidence into `ai-bom:git:*`
  properties without reading Git metadata from the exporter.
- Map parsed Python dependency packages to `library` components. Emit `version`
  only for exact pins or lockfile versions, and preserve requirement, marker,
  extras, source path, source type, and lockfile format as
  `ai-bom:dependency:*` properties.

## Required Fixtures

- Complete model project.
- Sparse model project.
- Invalid config.
- Missing artifact.
- Secret redaction.
- Symlink escape.
- Exporter schema failure.

## Schema Source

The official CycloneDX 1.7 JSON schema is vendored under
`src/ai_bom_generator/exporters/cyclonedx_json/schema/` together with its
upstream license file. Runtime exporter validation uses that vendored schema.

## Approval Criteria

- Generated CycloneDX JSON validates against the vendored official schema.
- Golden fixtures are deterministic.
- Warning report and JSON summary stay consistent with the BOM output.
- Mapping docs identify any field that is declared rather than independently verified.
- Git commit properties appear only when the collector resolved a detached HEAD
  or symbolic ref to a 40-character commit value.

## Review Blockers

- The exporter reads files directly instead of consuming normalized evidence.
- The exporter implies legal license conclusions or compliance approval.
- The exporter passes schema validation but loses warning or source-location context.
