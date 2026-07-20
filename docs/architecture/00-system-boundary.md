# System Boundary

Status: Draft

## Boundary

This repository owns the AI-BOM Generator CLI, optional GitHub Action wrapper,
collector contracts, exporter mappings, warning taxonomy, and fixture-based
validation for AI bill-of-materials generation.

It consumes local model project files, discovered or explicit config, model cards, dependency
lockfiles, dataset references, prompt references, eval references, Git metadata,
and selected model artifacts for hashing.

It does not own model training, dataset hosting, vulnerability scanning, legal
review, model registry operations, or model serving.

## Runtime Flow

1. User invokes the CLI or GitHub Action with a target model directory.
2. The tool loads explicit config, or discovers `<model-directory>/aibom.toml`,
   and discovers supported metadata files.
3. Collectors produce normalized evidence with source context.
4. Artifact hashing records deterministic digests for selected model files.
5. Exporter maps normalized evidence to the selected BOM format.
6. Reporter writes the BOM, warnings, and machine-readable summary.
7. Invalid required input or invalid exporter output fails the run; missing optional metadata is reported as warnings.

## Quality Attributes

- Maintainability: changes must preserve source-of-truth documents.
- Security: config, paths, and generated reports must avoid leaking secrets or private dataset contents.
- Operability: CI output must distinguish success, warnings, and failures without requiring hosted services.
- Determinism: stable input should produce a byte-stable BOM and warning report;
  elapsed summary timing and manifest generation identity remain run-specific.
- Honesty: generated BOM output must never imply audit completeness beyond the collected evidence.
