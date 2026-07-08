# AI-BOM Generator

Status: Draft
Scope: data
Repository Type: cli-tool
Addons: github-action

AI-BOM Generator is a small CLI and optional GitHub Action for producing an AI
bill of materials from a model project directory.

The tool records declared model metadata, discovered `MODEL_CARD.md` paths,
model or checkpoint digests, training-code references, dependency lockfiles,
dataset references, prompt templates, and eval artifact references, then exports
them to an existing BOM family such as SPDX AI or CycloneDX ML-BOM.

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
- discover in-root `MODEL_CARD.md` paths without copying model-card contents;
- compute SHA-256 digests for model artifacts and checkpoints;
- collect dependency and training-code references from known lockfile or config locations;
- read dataset, prompt, and eval references from explicit config;
- export one initial standards-backed BOM format;
- report missing metadata as warnings without pretending the BOM is complete.

## Quickstart

The first public MVP is distributed as a GitHub repository and GitHub Action.
PyPI packaging is deferred until package-registry policy is approved.

Try the bundled minimal project from a checkout:

```powershell
uv sync --locked
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-example-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 ai-bom generate examples/minimal-model-project --config examples/minimal-model-project/aibom.toml --format cyclonedx-json-1.7 --output (Join-Path $out "bom.cdx.json") --warning-report (Join-Path $out "warnings.json") --summary (Join-Path $out "summary.json")
Get-ChildItem -LiteralPath $out
```

The same command shape works for your own model project as long as generated
output paths resolve outside the target model directory.

Example `aibom.toml` from `examples/minimal-model-project`:

```toml
schema_version = "1"

[output]
format = "cyclonedx-json-1.7"

[model]
name = "example-model"
version = "0.1.0"
model_card = "MODEL_CARD.md"
license_declared = "NOASSERTION"

[artifacts]
include = ["models/*.safetensors"]

[[dependencies]]
path = "requirements.lock"
type = "pip"

[[datasets]]
name = "example-dataset"
license_declared = "NOASSERTION"
```

The CLI writes a BOM, a warning report, and a JSON summary. Missing optional
metadata is reported as machine-readable warnings. Unreadable required files,
invalid config, unsupported exporters, unsafe paths, and invalid generated BOM
output fail with non-zero exit codes. Generated output paths must resolve
outside the target model project directory.

## Current CLI Smoke

```text
ai-bom generate <model-directory> --config <path> --format cyclonedx-json-1.7 --output <bom.json> --warning-report <warnings.json> --summary <summary.json>
```

## Current GitHub Action Smoke

```yaml
- uses: actions/setup-python@v6
  with:
    python-version: "3.12"
- uses: astral-sh/setup-uv@v8.3.1
- uses: 0disoft/ai-bom-generator@v0.1.0
  with:
    model-directory: .
    config: aibom.toml
```

The action invokes the packaged CLI with `uv run --project`, so consuming
workflows must make Python 3.12 and `uv` available before this action runs. When
`format` or `warnings` inputs are omitted, the action lets the CLI use the
explicit config values and CLI defaults. Generated files are written to explicit
paths when provided, or to a run-unique directory under `RUNNER_TEMP`.

The current implementation validates explicit `aibom.toml` config files against
AI-BOM config schema v1, validates generated CycloneDX JSON 1.7 output against
the vendored official schema, and validates AI-BOM summary/warning contracts in
tests.

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

Runtime floor is Python 3.12, the initial CLI adapter is `argparse`, package
metadata lives in `pyproject.toml`, JSON Schema validation uses `jsonschema`,
the project lockfile is `uv.lock`, explicit config files use `aibom.toml`, the
first exporter is CycloneDX JSON 1.7, strict redaction is the default, and the
repository license is Apache-2.0. The first public MVP release uses immutable
GitHub tag `v0.1.0`; PyPI packaging, mutable major action tags, package manager
UX, second exporter priority, automatic config discovery, and model artifact
discovery defaults remain deferred until the repository owner records them in
the source-of-truth documents.
