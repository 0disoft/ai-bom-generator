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

These commands mirror the hosted CI workflow. The hosted validation matrix runs
the compile, lint, test, build, wheel, Action verifier, and CLI smoke gates on
every supported Python version: 3.12, 3.13, and 3.14. The local commands below
use the minimum supported runtime, Python 3.12.

| Validation name | Command |
| --- | --- |
| check | `uv sync --locked` |
| check | `uv run --python 3.12 python -m compileall -q src tests scripts` |
| lint | `uv run --python 3.12 ruff check src tests scripts` |
| test | `uv run --python 3.12 python -m unittest discover -s tests -v` |
| check | `uv run --python 3.12 python scripts/benchmark_components.py --check --json` |
| check | `uv build` |
| check | `uv run --python 3.12 python scripts/verify_wheel.py dist` |
| smoke | `uv run --python 3.12 python scripts/verify_github_action.py` |
| smoke | `uv run --python 3.12 python scripts/verify_release.py --version <released-version> --publish-run-id <run-id> --smoke-run-id <run-id>` |
| smoke | `uv run --python 3.12 ai-bom generate tests/fixtures/complete-project --format cyclonedx-json-1.7 --output <temp>/bom.cdx.json --warning-report <temp>/warnings.json --summary <temp>/summary.json` |
| check | `git diff --check` |

Docs validation is review-based until a documentation linter is configured.
Format, typecheck, contract, and migration-check are stable names but do not
have configured runners yet.

CodeQL is hosted-only validation. Its workflow is checked locally with
`actionlint`; analysis and security-event upload require GitHub's CodeQL runner
and are verified after the final push.

Dependabot configuration is validated locally as YAML and against the current
Dependabot 2.0 JSON Schema. Actual update proposal behavior is hosted-only and
is observed after the final push or next scheduled run.

`scripts/verify_wheel.py` verifies required package data, required synthetic
test fixtures in the source distribution, the `ai-bom` entry point metadata,
required runtime dependency metadata, installation of the built wheel into an
isolated virtual environment, `ai-bom --help`, `ai-bom --version`, and an
installed-console-script fixture smoke that relies on target-root config
discovery while using the locked validation environment for dependencies.

`scripts/verify_github_action.py` verifies the local composite `action.yml` and
runs clean, warning-only, fail-on-warning, stale-output, and manifest-gated
action wrapper smoke cases. External actions must use a full commit SHA with a
human-readable semantic-version comment, while Dependabot maintains both values.
Hosted CI separately invokes the local action on a
clean Ubuntu, macOS, and Windows runner matrix without caller-side Python or uv
setup. Matrix fail-fast is disabled so one platform failure does not hide the
other runner results.

`scripts/verify_release.py` verifies a published release by checking PyPI JSON,
published wheel and source distribution entries, installed console-script help
through `uv --with`, GitHub-enforced release immutability for post-enforcement
tags, the PyPI publish workflow run, and the external action smoke repository.
Known releases through `v0.2.0` predate repository-level enforcement and remain
an explicit verifier exception. The external smoke check reads
the dedicated `AI-BOM Release Smoke` workflow at the successful run's exact
`headSha` and requires one exact `owner/repository@v<version>` Action reference.
The separate mutable-channel workflow can remain on `@v0` without temporary
release-verification rewrites.
PyPI project-root metadata establishes package identity, while the exact-version
endpoint establishes the requested version and artifacts; a temporarily stale
project-root `latest` value does not create a false release failure.

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
