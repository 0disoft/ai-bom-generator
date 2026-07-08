# Minimal Model Project

This fixture is a tiny copy-paste target for AI-BOM Generator. It is not a real
model and does not contain production data.

From the repository root:

```powershell
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-example-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 ai-bom generate examples/minimal-model-project --format cyclonedx-json-1.7 --output (Join-Path $out "bom.cdx.json") --warning-report (Join-Path $out "warnings.json") --summary (Join-Path $out "summary.json")
Get-ChildItem -LiteralPath $out
```

The run should create `bom.cdx.json`, `warnings.json`, `summary.json`, and
`summary.json.manifest.json`. For this fixture, the summary reports a
`success` status, `complete` evidence, one artifact, and zero warnings. The CLI
discovers this fixture's `aibom.toml` from the target model directory.
