# Domain Model

Status: Draft

## Boundary

The domain model describes evidence that can be collected from a model project
directory and mapped into an AI/ML BOM. It must separate declared metadata,
observed files, derived hashes, missing metadata warnings, and generated output.

## Domain Objects

- Target project: caller-owned model directory.
- Model metadata: model card or manifest fields discovered from supported files.
- Model artifact: checkpoint, weight, or related file selected for digesting.
- Dependency evidence: explicit lockfile or dependency manifest reference.
- Dependency package: normalized Python package name, evidenced exact version or
  requirement expression, source format/type, marker, extras, and source
  location parsed from a supported dependency file.
- Training reference: script path, commit reference, or declared training pipeline reference.
- Dataset reference: declared source, version, license, or provenance pointer; not dataset contents.
- Prompt reference: declared prompt template or prompt artifact pointer.
- Eval reference: declared evaluation dataset, run, metric, or artifact pointer.
- Normalized evidence: internal representation used by exporters.
- BOM artifact: generated standards-backed output.
- Warning report: missing, ambiguous, unsupported, or incomplete metadata.

## Quality Attributes

- Maintainability: changes must preserve source-of-truth documents.
- Security: domain objects must not require private dataset contents or secrets.
- Operability: every warning should identify the affected object and source context.
- Determinism: domain objects should serialize in stable order for stable input.
