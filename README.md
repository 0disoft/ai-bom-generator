# AI-BOM Generator

[![PyPI](https://img.shields.io/pypi/v/ai-bom-generator.svg)](https://pypi.org/project/ai-bom-generator/)
[![CI](https://github.com/0disoft/ai-bom-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/0disoft/ai-bom-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/0disoft/ai-bom-generator)](https://github.com/0disoft/ai-bom-generator/releases)
[![License](https://img.shields.io/pypi/l/ai-bom-generator.svg)](LICENSE)

AI-BOM Generator is a small Python 3.12 CLI and GitHub Action for producing an
AI/ML bill of materials from a local model project directory.

It records declared model metadata, in-root `MODEL_CARD.md` paths, model or
checkpoint digests, training-code references, dependency lockfiles, dataset
references, prompt templates, and eval artifact references, then exports
CycloneDX JSON 1.7.

It is an evidence reporter. It is not a model registry, vulnerability scanner,
legal compliance engine, dataset auditor, or AI governance platform.

## Install

```powershell
py -3.12 -m pip install ai-bom-generator
ai-bom --version
ai-bom --help
```

With `uv`, you can run the published package without installing it into the
current environment:

```powershell
uv run --python 3.12 --with ai-bom-generator ai-bom --version
uv run --python 3.12 --with ai-bom-generator ai-bom --help
```

## Quickstart

Clone the repository so the bundled minimal model project is available:

```powershell
git clone https://github.com/0disoft/ai-bom-generator.git
cd ai-bom-generator
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-example-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 --with ai-bom-generator ai-bom generate examples/minimal-model-project --config examples/minimal-model-project/aibom.toml --format cyclonedx-json-1.7 --output (Join-Path $out "bom.cdx.json") --warning-report (Join-Path $out "warnings.json") --summary (Join-Path $out "summary.json")
Get-ChildItem -LiteralPath $out
```

Expected files:

```text
bom.cdx.json
summary.json
summary.json.manifest.json
warnings.json
```

For the bundled minimal project, `summary.json` reports
`"status": "success"`, `"completeness_status": "complete"`,
`"artifact_count": 1`, and `"warning_count": 0`.

The command writes:

- `bom.cdx.json`: CycloneDX JSON 1.7 BOM.
- `warnings.json`: machine-readable warning report.
- `summary.json`: generation status and output summary.
- `summary.json.manifest.json`: output-set manifest when the default manifest path is used.

Generated output paths must resolve outside the target model project directory.

## Minimal Config

Example `aibom.toml`:

```toml
schema_version = "1"

[output]
format = "cyclonedx-json-1.7"

[model]
name = "minimal-example-model"
version = "0.1.0"
model_card = "MODEL_CARD.md"
license_declared = "NOASSERTION"

[artifacts]
include = ["models/*.safetensors"]

[[dependencies]]
path = "requirements.lock"
type = "pip"

[[datasets]]
name = "minimal-example-dataset"
license_declared = "NOASSERTION"
```

The current MVP reads explicit config files only. Automatic config discovery,
artifact discovery defaults, SPDX export, and GitHub Marketplace registration
are deferred.

## CLI

```text
ai-bom --version
ai-bom generate <model-directory> --config <path> --format cyclonedx-json-1.7 --output <bom.json> --warning-report <warnings.json> --summary <summary.json> [--manifest <manifest.json>]
```

Missing optional metadata is reported as warnings without pretending the BOM is
complete. Unreadable required files, invalid config, unsupported exporters,
unsafe paths, and invalid generated BOM output fail with non-zero exit codes.

## GitHub Action

```yaml
- uses: actions/checkout@v7

- uses: actions/setup-python@v6
  with:
    python-version: "3.12"

- uses: astral-sh/setup-uv@v8.3.1

- id: ai-bom
  uses: 0disoft/ai-bom-generator@v0
  with:
    model-directory: .
    config: aibom.toml
    warnings: allow

- name: Verify AI-BOM outputs
  shell: bash
  run: |
    set -euo pipefail
    test -s "${{ steps.ai-bom.outputs.bom-path }}"
    test -s "${{ steps.ai-bom.outputs.warning-report-path }}"
    test -s "${{ steps.ai-bom.outputs.summary-path }}"
    test "${{ steps.ai-bom.outputs.status }}" = "success"
```

The action invokes the packaged CLI with `uv run --project`, so consuming
workflows must make Python 3.12 and `uv` available before this action runs.
The current `v0` contract intentionally keeps Python and `uv` setup
caller-managed instead of installing toolchains inside the action.
When `format` or `warnings` inputs are omitted, the action lets the CLI use the
explicit config values and CLI defaults. Generated files are written to explicit
paths when provided, or to a run-unique directory under `RUNNER_TEMP`.

Summary-derived action outputs are published only when the generation manifest
matches the BOM, warning report, and summary files from the current run.

Use `@v0` for compatible patch updates, or pin an immutable patch tag such as
`@v0.1.2` when a workflow needs exact release reproducibility.

## Validation

Local validation source of truth is [VALIDATION.md](VALIDATION.md).

```powershell
uv sync --locked
uv run --python 3.12 python -m compileall -q src tests scripts
uv run --python 3.12 ruff check src tests scripts
uv run --python 3.12 python -m unittest discover -s tests -v
uv build
uv run --python 3.12 python scripts/verify_wheel.py dist
uv run --python 3.12 python scripts/verify_github_action.py
```

Post-release verification:

```powershell
uv run --python 3.12 python scripts/verify_release.py --version 0.1.2 --publish-run-id 28930381437
```

## Project Docs

- [Product spec](docs/product/02-spec.md)
- [CLI contract](docs/cli/command-contract.md)
- [GitHub Action contract](docs/github-action/action-contract.md)
- [Release operations](docs/ops/release.md)
- [Changelog](CHANGELOG.md)

## License

Apache-2.0.
