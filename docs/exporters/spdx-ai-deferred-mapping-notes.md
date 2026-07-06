# SPDX AI Deferred Mapping Notes

Status: Draft
Owner: UNASSIGNED

## Purpose

SPDX AI is an important target, but it should remain deferred until the first
exporter proves the normalized evidence model and warning taxonomy.

## Deferral Reasons

- SPDX AI mapping may need careful treatment of declared versus concluded license fields.
- Dataset profile behavior must not make this tool look like a legal or dataset audit engine.
- The internal model must stay exporter-independent before adding a second exporter.

## Future Mapping Questions

- How should `NOASSERTION` and raw declared license strings be represented?
- Which AI, Dataset, Licensing, Security, and Build profile relationships are needed?
- Which fields require human declaration rather than tool observation?
- Which conformance fixtures prove import/export compatibility?

## Review Blockers

- SPDX output is added before CycloneDX mapping fixtures or equivalent first-exporter fixtures are stable.
- SPDX fields are added directly to collector or domain object names.
- SPDX output claims concluded license, model safety, or compliance status without explicit human input.
