# Architecture

Status: Draft

## Boundary

AI-BOM Generator owns a local CLI, optional GitHub Action wrapper, collector
contracts, exporter mappings, warning taxonomy, and validation fixtures for
generating AI/ML bill-of-materials artifacts from a model project directory.

It consumes caller-owned local files: model cards, metadata manifests, selected
model artifacts or checkpoints, dependency lockfiles, training-code references,
dataset references, prompt references, eval references, and Git metadata.

It does not own model serving, model registry behavior, hosted storage,
vulnerability scanning, legal license decisions, compliance approval, or
training-data audits.

## Runtime Flow

1. Resolve the target model directory and explicit config.
2. Discover supported metadata and artifact inputs without mutating the caller project.
3. Normalize collector evidence with source locations and absence information.
4. Hash selected model artifacts with a deterministic digest algorithm.
5. Map normalized evidence into the selected standards-backed BOM format.
6. Write the BOM, warning report, and JSON automation summary.
7. Fail on invalid required input, hash errors, or exporter errors; warn on missing optional metadata.

## Quality Attributes

- Maintainability: changes must preserve source-of-truth documents.
- Security: input paths, summaries, logs, and artifacts must avoid leaking secrets or private dataset contents.
- Operability: CI and local runs must distinguish success, warnings, and hard failures.
- Determinism: stable input should produce stable output.
- Honesty: generated BOM output must not imply evidence that was not collected.
