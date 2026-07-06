# AGENTS.md

## Repository Scope

Scope: data

This repository owns data pipeline contracts, lineage, quality gates, retention decisions,
privacy boundaries, and data validation surfaces.

This repository does not generate production datasets, credentials, or warehouse
objects. Application runtime code is allowed only for the approved local CLI and
GitHub Action wrapper scope described in docs/product/02-spec.md and docs/adr/.

## Repository Shape

Primary repository type: cli-tool
Addons: github-action

- cli-tool: This repository type owns command behavior, arguments, flags, config loading, exit codes, terminal output, JSON output, runtime compatibility, and shell integration contracts.
- github-action: This repository type owns action inputs, outputs, permissions, token handling, and runner compatibility.


## Source of Truth

- Product scope: docs/product/02-spec.md
- Architecture decisions: docs/adr/*.md
- Validation: VALIDATION.md
- Agent routing: .agents/context-map.md
- Repository hygiene: .editorconfig, .gitattributes, .gitignore

## Implementation Mode

Owner-approved implementation started on 2026-07-06.

Approved implementation decisions:

- Runtime floor: Python 3.12.
- CLI adapter: argparse, isolated from application and domain layers.
- Repository license: Apache-2.0.

Implementation may add local CLI source code, tests, synthetic fixtures, schemas,
and packaging metadata when those changes preserve the source-of-truth contracts.

## Hard Rules

- Do not generate production datasets, credentials, warehouse objects, hosted
  services, or model-serving runtime code.
- Do not invent technology choices. Use UNDECIDED when a decision is not known.
- Do not create fake credentials, tokens, secrets, or private values.
- Do not rely on generated, cache, or build output as source truth.

## Repository Hygiene

- .editorconfig sets line ending, encoding, and final newline policy.
- .gitattributes sets Git text normalization and binary diff policy.
- .gitignore excludes local, secret, build, and cache artifacts.
- Generated, cache, and build output must not be used as design-document evidence.
- Do not create large diffs that only change line endings.

## Before Editing

- Read this file, VALIDATION.md, CHECKLIST.md, and .agents/context-map.md.
- Read the skill and checklist named by the context map.
- Confirm source-of-truth documents before changing contracts.

## Out of Scope

- Production datasets, dataset hosting, and warehouse objects.
- Runtime infrastructure such as Docker, Kubernetes, Terraform, or framework apps.
- Project-specific credentials or deployment secrets.

## Final Response Requirements

- List executed validations, passed validations, skipped validations, skip reasons, and remaining risk.
- Name any source-of-truth documents changed.
- Call out API, DB, repository hygiene, and runner changes explicitly.
