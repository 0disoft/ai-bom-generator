# CI

Status: Draft

## Operational Contract

CI must prove the CLI/action contract with docs checks, fixture tests, exporter
validation once an exporter is selected, deterministic output checks, and
permission review for the GitHub Action wrapper.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: failing check/test/docs validation, nondeterministic fixture output, or action permission drift blocks release.
- Remaining operational risk: exact branch protection and hosted CI matrix remain UNDECIDED.

## Hosted Workflow

The repository CI workflow lives at `.github/workflows/ci.yml`.

- Trigger: pull requests and pushes to `main`.
- Runner: `ubuntu-latest`.
- Runtime: Python 3.12.
- Environment manager: `uv`, locked by `uv.lock`.
- Action pins: `actions/checkout@v7.0.0`, `actions/setup-python@v6.3.0`,
  and `astral-sh/setup-uv@v8.2.0`.
- Permissions: `contents: read`.

The workflow intentionally does not upload artifacts, write pull request
comments, attach releases, publish packages, or request secrets. Those behaviors
belong to future GitHub Action wrapper decisions and must stay opt-in.

## CI Validation Steps

| Validation name | CI step |
| --- | --- |
| check | Install locked environment with `uv sync --locked`. |
| check | Compile `src` and `tests` with `python -m compileall`. |
| test | Run `python -m unittest discover -s tests -v`. |
| check | Build source and wheel distributions with `uv build`. |
| smoke | Generate a CycloneDX JSON 1.7 BOM, warning report, and summary from `tests/fixtures/complete-project` through the `ai-bom` console script. |
| check | Run `git diff --check` for whitespace and diff hygiene. |

Docs validation is performed by reviewing changed documentation until a
dedicated docs runner is configured.

## Local Reproduction

Run these commands from the repository root:

```powershell
uv sync --locked
uv run --python 3.12 python -m compileall -q src tests
uv run --python 3.12 python -m unittest discover -s tests -v
uv build
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-ci-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 ai-bom generate tests/fixtures/complete-project --config tests/fixtures/complete-project/aibom.toml --format cyclonedx-json-1.7 --output $(Join-Path $out "bom.cdx.json") --warning-report $(Join-Path $out "warnings.json") --summary $(Join-Path $out "summary.json")
git diff --check
```

## Rollback

If the hosted workflow blocks unrelated work, revert the workflow commit or
disable the CI workflow in GitHub while preserving the local validation commands
in `VALIDATION.md` as the source of truth for manual checks.
