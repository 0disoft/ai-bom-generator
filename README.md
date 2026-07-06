# AI-BOM Generator

Status: Draft
Scope: data
Repository Type: cli-tool
Addons: github-action

AI-BOM Generator is a small CLI and optional GitHub Action for producing an AI
bill of materials from a model project directory.

The tool will collect model cards, model or checkpoint digests, training-code
references, dependency lockfiles, dataset references, prompt templates, and eval
artifact references, then export them to an existing BOM family such as SPDX AI
or CycloneDX ML-BOM.

It is a generator and evidence reporter. It is not a model registry, scanner,
legal compliance engine, dataset auditor, or AI governance platform.

## Source Files

- AGENTS.md: agent working rules
- CHECKLIST.md: checklist router
- VALIDATION.md: validation names and reporting requirements
- .agents/context-map.md: agent route map
- docs/product/02-spec.md: product source of truth
- docs/cli/command-contract.md: CLI contract source
- docs/github-action/action-contract.md: GitHub Action contract source
- docs/data/pipeline-contract.md: artifact collection and export contract
- docs/: design, operations, architecture, and engineering standards

## Repository Shape Notes

- cli-tool: This repository type owns command behavior, arguments, flags, config loading, exit codes, terminal output, JSON output, runtime compatibility, and shell integration contracts.
- github-action: This repository type owns action inputs, outputs, permissions, token handling, and runner compatibility.

## MVP Direction

- accept one model directory as input;
- discover model cards and optional project manifests;
- compute SHA-256 digests for model artifacts and checkpoints;
- collect dependency and training-code references from known lockfile or config locations;
- read dataset, prompt, and eval references from explicit config;
- export one initial standards-backed BOM format;
- report missing metadata as warnings without pretending the BOM is complete.

## Non-Goals

- no automatic legal license judgment;
- no training-data audit guarantee;
- no vulnerability scanner;
- no model serving runtime;
- no hosted registry;
- no broad "all ML frameworks" promise until fixtures prove it.

## Repository Hygiene

.editorconfig, .gitattributes, and .gitignore are generated to keep line endings,
binary diffs, local files, build outputs, caches, and secret files under control.

## Scope Notes

Implementation language, package manager, runtime floor, SPDX/CycloneDX exporter
priority, and release packaging remain UNDECIDED until the repository owner records
them in the source-of-truth documents.
