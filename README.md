# AI-BOM Generator

[![PyPI](https://img.shields.io/pypi/v/ai-bom-generator.svg)](https://pypi.org/project/ai-bom-generator/)
[![CI](https://github.com/0disoft/ai-bom-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/0disoft/ai-bom-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/0disoft/ai-bom-generator)](https://github.com/0disoft/ai-bom-generator/releases)
[![License](https://img.shields.io/pypi/l/ai-bom-generator.svg)](LICENSE)

AI-BOM Generator is a small Python 3.12 CLI and GitHub Action for producing an
AI/ML bill of materials from a local model project directory.

It records declared model metadata, in-root `MODEL_CARD.md` paths, model or
checkpoint digests, training-code references, dependency files and parsed
Python packages, dataset references, prompt templates, and eval artifact
references, then exports CycloneDX JSON 1.7 or an SPDX 3.0.1 AI Profile preview.

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
uv sync --locked
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-example-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 ai-bom generate examples/minimal-model-project --format cyclonedx-json-1.7 --output (Join-Path $out "bom.cdx.json") --warning-report (Join-Path $out "warnings.json") --summary (Join-Path $out "summary.json")
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

Explicit `uv.lock` and requirements-file references are parsed locally into
package components by default. Set `parse = false` on a dependency reference
to keep file-level evidence only. Includes, constraints, editable requirement
directives, resolution, downloads, and automatic lockfile discovery are not
performed.

When `--config` is omitted, the CLI reads `aibom.toml` from the target model
directory if that file exists. It does not search parent directories or alternate
filenames. Artifact discovery defaults are opt-in with
`[artifacts].discovery = true`. The `spdx-ai` export format is available as a
partial SPDX 3.0.1 AI Profile preview; it explicitly marks unavailable SPDX AI
fields instead of inventing missing metadata. GitHub Marketplace registration is
deferred.

## CLI

```text
ai-bom --version
ai-bom generate <model-directory> [--config <path>] --format <cyclonedx-json-1.7|spdx-ai> --output <bom.json> --warning-report <warnings.json> --summary <summary.json> [--manifest <manifest.json>]
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
  with:
    enable-cache: false

- id: ai-bom
  uses: 0disoft/ai-bom-generator@v0
  with:
    model-directory: .
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

Starting with the unreleased `v0.2.0` contract, the action prepares Python 3.12
and pinned uv `0.11.28`, disables the setup-uv GitHub cache, and invokes the
packaged CLI with `uv run --project --locked`. Its virtual environment and uv
download cache stay under `RUNNER_TEMP`; the caller repository is not used for
action runtime state. The setup steps remain in this example until mutable tag
`v0` moves to `v0.2.0`, so it also works with the currently published action.
When `format` or `warnings` inputs are omitted, the action lets the CLI use the
discovered or explicit config values and CLI defaults. Generated files are
written to explicit paths when provided, or to a run-unique directory under
`RUNNER_TEMP`.

Summary-derived action outputs are published only when the generation manifest
matches the BOM, warning report, and summary files from the current run.

Use `@v0` for compatible patch updates, or pin the immutable `@v0.1.4` tag
when a workflow needs exact release reproducibility.

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
$env:RELEASE_VERSION = "0.1.4"
$env:PUBLISH_RUN_ID = "<successful-publish-run-id>"
uv run --python 3.12 python scripts/verify_release.py --version $env:RELEASE_VERSION --publish-run-id $env:PUBLISH_RUN_ID
```

## Project Docs

- [Product spec](docs/product/02-spec.md)
- [CLI contract](docs/cli/command-contract.md)
- [GitHub Action contract](docs/github-action/action-contract.md)
- [Release operations](docs/ops/release.md)
- [Changelog](CHANGELOG.md)

## License

Apache-2.0.
