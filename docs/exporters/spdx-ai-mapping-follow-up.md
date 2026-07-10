# SPDX AI Mapping Follow-up

Status: Draft
Owner: UNASSIGNED

## Purpose

The `spdx-ai` exporter now provides a partial SPDX 3.0.1 AI Profile preview.
This note tracks the remaining work between that bounded preview contract and
full upstream SPDX conformance.

## Implemented Baseline

- CycloneDX and SPDX AI exporters share an exporter-independent normalized
  evidence model.
- The SPDX AI preview validates against the local preview schema.
- Unavailable and unsupported SPDX AI fields are listed explicitly instead of
  being fabricated.

## Remaining Mapping Questions

- How should `NOASSERTION` and raw declared license strings be represented?
- Which AI, Dataset, Licensing, Security, and Build profile relationships are needed?
- Which fields require human declaration rather than tool observation?
- Which conformance fixtures prove import/export compatibility?
- Which upstream JSON-LD or SHACL validator should become the executable
  conformance gate?

## Review Blockers

- The preview is described as fully SPDX-conformant before an upstream
  conformance gate exists.
- SPDX fields are added directly to collector or domain object names.
- SPDX output claims concluded license, model safety, or compliance status without explicit human input.
