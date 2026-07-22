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
- Remaining operational risk: exact branch protection remains UNDECIDED.

## Hosted Workflow

The repository CI workflow lives at `.github/workflows/ci.yml`.

- Trigger: pull requests and pushes to `main`.
- Runner: `ubuntu-latest`.
- Package runtime matrix: Python 3.12, 3.13, and 3.14. The published composite
  Action intentionally provisions Python 3.12 as its managed runtime.
- Component performance: Python 3.12 runs the documented 100, 500, and 1,000
  component median-runtime and traced-allocation regression gate once per CI
  workflow to avoid tripling the benchmark cost across the compatibility matrix.
- Environment manager: `uv`, locked by `uv.lock`.
- Action dependencies use exact semantic-version pins. The current values are
  owned by `.github/workflows/*.yml` and `action.yml`.
- Permissions: `contents: read`.
- Managed-runtime smoke: a clean `ubuntu-latest`, `macos-latest`, and
  `windows-latest` matrix checks out the repository and invokes `uses: ./`
  without caller-side Python or uv setup. Fail-fast is disabled so every runner
  reports its own result.

The workflow intentionally does not upload artifacts, write pull request
comments, attach releases, publish packages, or request secrets. Release
publishing is isolated in `.github/workflows/publish-pypi.yml`.

`.github/workflows/clarissimi.yml` is the single deliberate moving-Action
exception. It follows the maintainer-promoted `0disoft/clarissimi@v0` channel
so contributor-recognition fixes arrive without a repository edit. The
pre-merge decision job is read-only and advisory by default. Merged pull
requests create only a review draft; an approved draft is promoted through a
second proposal pull request. Its proposal jobs persist checkout credentials
only for their scoped branch push and do not commit directly to `main`.

The workflow intentionally has no provider token. Its deterministic initial
draft is only an inbox scaffold: a maintainer or delegated coding agent must
replace or correct the assessment, change its approval status, and merge that
draft before dispatching `promote-draft` with the exact checked-in draft path.
After the advisory flow has been exercised, repository variable
`CLARISSIMI_GATE_MODE=required` can make the existing decision job fail closed
without renaming the check.

Repository-level smoke uses a documentation-only source pull request and
closes the generated Clarissimi draft without promotion, so test-only
assessment data never enters the contributor ledger.

## CodeQL Workflow

The repository CodeQL workflow lives at `.github/workflows/codeql.yml`.

- Triggers: pull requests and pushes targeting `main`, plus a weekly scheduled
  scan at `03:23 UTC` on Wednesday.
- Runner: `ubuntu-latest`.
- Language and build mode: Python with `build-mode: none`.
- Action dependencies use exact semantic-version pins. The current values are
  owned by `.github/workflows/codeql.yml`.
- Permissions: `contents: read` and `security-events: write` only.

CodeQL result upload is the only reason this workflow receives
`security-events: write`. It does not publish packages, upload generated BOMs,
request secrets, or mutate repository contents.

## Dependency Update Automation

Dependabot version updates are configured in `.github/dependabot.yml`.

- Ecosystems: root `uv` project and GitHub Actions.
- Schedule: weekly on Monday at `04:17 UTC` for Python dependencies and
  `04:27 UTC` for Actions.
- Pull request limit: three open version-update PRs per ecosystem.
- Grouping: one grouped PR per ecosystem to limit update noise.
- Authority boundary: Dependabot may propose lockfile and Action-reference
  changes through pull requests. It cannot merge, publish, tag, or release.

## PyPI Publish Workflow

The PyPI publish workflow lives at `.github/workflows/publish-pypi.yml`.

- Trigger: strict semver-like tags matching `vMAJOR.MINOR.PATCH`, plus manual
  dispatch for an existing release tag.
- Runner: `ubuntu-latest`.
- Runtime: Python 3.12.
- Environment manager: `uv`, locked by `uv.lock`.
- Action dependencies use exact semantic-version pins. The current values are
  owned by `.github/workflows/publish-pypi.yml`.
- Permissions: `contents: read` and job-scoped `id-token: write`.
- GitHub environment: `pypi`.

The publish workflow rebuilds and re-runs the same local validation contract as
CI before uploading distributions from `dist/`. It does not use PyPI API token
secrets. Uploads require the PyPI project to have a trusted publisher configured
for this repository, the `publish-pypi.yml` workflow, and the `pypi`
environment.

The workflow refuses to publish when the tag is not strict `vMAJOR.MINOR.PATCH`,
when the tag does not match `pyproject.toml` exactly, or when the version is an
existing GitHub-only tag (`0.1.0` or `0.1.1`).

## CI Validation Steps

| Validation name | CI step |
| --- | --- |
| check | Install locked environment with `uv sync --locked`. |
| check | Compile `src`, `tests`, and `scripts` with `python -m compileall`. |
| lint | Run `ruff check src tests scripts`. |
| test | Run `python -m unittest discover -s tests -v`. |
| check | Build source and wheel distributions with `uv build`, then verify the wheel and required synthetic sdist fixtures. |
| check | Verify the wheel includes runtime schemas, the `ai-bom` console script entry point, and required runtime dependency metadata; installs into an isolated virtual environment without dependency resolution; renders `ai-bom --help` and `ai-bom --version`; and can run an installed-console-script fixture smoke with the locked validation dependencies. |
| smoke | Verify the composite GitHub Action wrapper with clean, warning-only, fail-on-warning, stale-output, and manifest-gated output fixture cases. |
| smoke | Generate a CycloneDX JSON 1.7 BOM, warning report, summary, and generation manifest from `tests/fixtures/complete-project` through the `ai-bom` console script using target-root config discovery. |
| check | Run `git diff --check` for whitespace and diff hygiene. |

Docs validation is performed by reviewing changed documentation until a
dedicated docs runner is configured.

## Local Reproduction

Run these commands from the repository root:

```powershell
uv sync --locked
uv run --python 3.12 python -m compileall -q src tests scripts
uv run --python 3.12 ruff check src tests scripts
uv run --python 3.12 python -m unittest discover -s tests -v
uv build
uv run --python 3.12 python scripts/verify_wheel.py dist
uv run --python 3.12 python scripts/verify_github_action.py
$out = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-bom-ci-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $out | Out-Null
uv run --python 3.12 ai-bom generate tests/fixtures/complete-project --format cyclonedx-json-1.7 --output $(Join-Path $out "bom.cdx.json") --warning-report $(Join-Path $out "warnings.json") --summary $(Join-Path $out "summary.json")
git diff --check
```

The Action verifier also rejects external `uses:` entries unless they use a
full lowercase commit SHA followed by a human-readable semver comment. CI,
release, CodeQL, and the published composite Action use uv `0.11.28`; the
Dependabot GitHub Actions updater maintains SHA pins and version comments.

## Rollback

If the hosted workflow blocks unrelated work, revert the workflow commit or
disable the CI workflow in GitHub while preserving the local validation commands
in `VALIDATION.md` as the source of truth for manual checks.
