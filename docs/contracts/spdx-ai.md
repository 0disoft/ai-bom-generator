# SPDX AI Preview Contract

Status: Draft
Repository Type: cli-tool

## Purpose

The `spdx-ai` exporter emits an SPDX-oriented JSON-LD document for local AI/ML
project evidence without claiming that every SPDX AI Profile field can be
derived from the current collector model.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- SPDX target: SPDX 3.0.1 AI Profile, preview mapping
- Executable contract schema: schemas/aibom-spdx-ai-preview.schema.json

## Format Name

The public CLI and config format name is `spdx-ai`.

The output declares:

- `@context`: `https://spdx.org/rdf/3.0.1/spdx-context.jsonld`
- `aiBom:spdxTarget`: `SPDX 3.0.1 AI Profile preview`
- `aiBom:conformance`: `partial`
- `aiBom:contract`: `docs/contracts/spdx-ai.md`

The exporter validates this local preview contract before writing output. It
does not yet perform full upstream SPDX SHACL or JSON-LD conformance validation.

`CreationInfo` identifies the generating tool but intentionally omits `created`.
The normalized evidence model has no trustworthy source creation timestamp, and
using the wall-clock generation time would make identical inputs produce
different BOMs. A future timestamp field requires an explicit evidence source
and contract update.

## Mapping

| AI-BOM evidence | SPDX-oriented element |
| --- | --- |
| Model metadata | `ai_AIPackage` root element |
| Model `name` | `ai_AIPackage.name` |
| Model `version` | `ai_AIPackage.packageVersion`; `NOASSERTION` when absent |
| Model `model_card` | `aiBom:modelCard` extension field |
| Model `license_declared` | `aiBom:licenseDeclared` extension field |
| Model `release_time` or `release_date` | `aiBom:releaseTime` extension field; preserved as declared evidence |
| Producer generation marker | `aiBom:generationMarkerPath` and `aiBom:generationMarkerSha256`; raw generation omitted |
| Artifact paths and SHA-256 digests | `software_File` elements with `verifiedUsing` |
| Parsed dependency packages | `software_Package` elements; `packageVersion` is `NOASSERTION` when no exact version is evidenced, while normalized source fields and artifact hashes use `aiBom:*` extension fields |
| Dependency, dataset, prompt, eval, training, and Git references | `aiBom_Reference` extension elements |
| Evidence containment | One `Relationship` from the model to collected evidence elements |
| Warning and completeness state | `aiBom:warningCount` and `aiBom:completenessStatus` |

All generated SPDX ids use the stable `urn:ai-bom-generator:spdx-ai:` namespace.
Dependency package source evidence is emitted as `aiBom:sourceType`, optional
`aiBom:sourceLocator`, `aiBom:sourceChannel`, `aiBom:sourceIndex`,
`aiBom:sourcePlatform`, and `aiBom:sourceRevision` fields. Bounded artifact hash
evidence is emitted as `aiBom:artifactHashes` objects with `algorithm`,
`hashValue`, and an optional strict-redacted `locator`.

## Explicit Gaps

The exporter records unavailable or unsupported SPDX AI fields inside the root
model package instead of silently implying that they were known.

- `aiBom:unavailableSpdxAiFields` lists SPDX AI fields that are important for
  the target profile but absent from current local evidence, such as
  `suppliedBy`, `downloadLocation`, and `releaseTime`.
- `aiBom:unsupportedSpdxAiFields` lists AI Profile fields that the current
  normalized evidence model does not yet support, such as metrics, safety risk
  assessment, energy consumption, and sensitive personal information.

These fields are informational and do not make the output a full SPDX AI
Profile conformance claim.

## Review Blockers

- The exporter claims full SPDX AI conformance without upstream conformance
  validation.
- The exporter fabricates supplier, download, release-time, safety, metric, or
  dataset-sensitive metadata.
- The exporter drops evidence without documenting the unsupported field or
  extension mapping.
- The exporter reads additional files or performs network access during export.
