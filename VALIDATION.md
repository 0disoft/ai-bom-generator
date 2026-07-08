# Validation

Status: Draft

## Validation Source of Truth

This document owns stable validation names for this scaffold.

## Standard Validation Names

- format
- lint
- typecheck
- test
- contract
- migration-check
- smoke
- docs
- check

## Current Local Validation Commands

These commands mirror the hosted CI workflow for the current Python 3.12 CLI
implementation.

| Validation name | Command |
| --- | --- |
| check | `uv sync --locked` |
| check | `uv run --python 3.12 python -m compileall -q src tests scripts` |
| lint | `uv run --python 3.12 ruff check src tests scripts` |
| test | `uv run --python 3.12 python -m unittest discover -s tests -v` |
| check | `uv build` |
| check | `uv run --python 3.12 python scripts/verify_wheel.py dist` |
| smoke | `uv run --python 3.12 python scripts/verify_github_action.py` |
| smoke | `uv run --python 3.12 python scripts/verify_release.py --version <released-version> --publish-run-id <run-id>` |
| smoke | `uv run --python 3.12 ai-bom generate tests/fixtures/complete-project --config tests/fixtures/complete-project/aibom.toml --format cyclonedx-json-1.7 --output <temp>/bom.cdx.json --warning-report <temp>/warnings.json --summary <temp>/summary.json` |
| check | `git diff --check` |

Docs validation is review-based until a documentation linter is configured.
Format, typecheck, contract, and migration-check are stable names but do not
have configured runners yet.

`scripts/verify_wheel.py` verifies required package data, the `ai-bom` entry
point metadata, installation of the built wheel into an isolated virtual
environment, `ai-bom --help`, `ai-bom --version`, and an
installed-console-script fixture smoke using the locked validation environment
for dependencies.

`scripts/verify_github_action.py` verifies the local composite `action.yml` and
runs clean, warning-only, fail-on-warning, stale-output, and manifest-gated
action wrapper smoke cases.

`scripts/verify_release.py` verifies a published release by checking PyPI JSON,
published wheel and source distribution entries, installed console-script help
through `uv --with`, the immutable GitHub Release, the PyPI publish workflow
run, and the external action smoke repository.

## Required Final Report

Final responses must list executed validations, passed validations, skipped validations, skip reasons, and remaining risk.

## Runner Policy

Task runner files are optional. Runner `none` means no executable task runner is generated.
If a runner is generated, runner command names must match this document.
Unconfigured runner commands must fail, not pass with a fake success.

## Hygiene Validation

Repository hygiene file changes must check line-ending churn, binary diff pollution,
tracked secret files, ignored build/cache artifacts, and generated-output drift.

## Scope

data validation routes must stay stack-neutral unless a runner file explicitly defines a command.

## Repository Shape

cli-tool, github-action validation must stay repository-shape focused and must not imply generated application source code.
