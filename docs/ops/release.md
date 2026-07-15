# Release

Status: Draft

## Operational Contract

Release policy must cover CLI package publishing, GitHub Action tag behavior,
documentation updates, exporter compatibility, fixture evidence, and how users
are told about warning or output contract changes.

Public release should wait until the repository has an Apache-2.0 LICENSE file,
security policy, complete and sparse fixtures, secret-redaction fixtures,
exporter validation, README non-goal language, and a rollback path for the
CLI/action contract.

The first public MVP release is `v0.1.0`. Releases through `v0.2.0` predate
GitHub's repository-level immutable-release enforcement and are preserved by
project policy. Repository-level enforcement is now enabled, so releases after
`v0.2.0` must report `isImmutable: true` and receive GitHub's tag, asset, and
attestation protections. Exact semver tags may be used directly as GitHub Action
refs. The mutable `v0` action tag may point
to the latest compatible 0.x action release after external smoke verification.
GitHub Marketplace registration and generated artifact upload are deferred until
explicitly approved.

PyPI package metadata is maintained in `pyproject.toml` with classifiers,
keywords, and project URLs. Package distributions must validate their README
rendering and wheel contents before upload.

## PyPI Publishing Policy

PyPI publishing is approved for strict semver releases after the package registry setup
is complete. Do not reuse a GitHub-only tag for a first package upload.

PyPI uploads must use PyPI Trusted Publishing from a GitHub Actions workflow.
Do not commit, document, or rely on long-lived PyPI API tokens for normal
publishing. Before an upload, the maintainer must:

- create or claim the PyPI project ownership for `ai-bom-generator`;
- configure the matching PyPI trusted publisher for this GitHub repository and
  release workflow;
- recheck package and version availability immediately before publish;
- run the full `VALIDATION.md` check set, including wheel verification and the
  GitHub Action wrapper smoke;
- confirm an external repository smoke has passed against the latest immutable
  GitHub Action tag;
- publish from a new immutable semver tag and mark rollback guidance in the GitHub Release
  notes if the package is broken.

The prepared publish workflow is `.github/workflows/publish-pypi.yml`. It runs
on strict `vMAJOR.MINOR.PATCH` tags and manual dispatch for an existing tag,
uses the GitHub `pypi` environment, requests job-scoped `id-token: write`, and
publishes with PyPI Trusted Publishing. The workflow rebuilds distributions and
re-runs compile, lint, unit/contract tests, wheel verification, GitHub Action
wrapper smoke, CLI fixture smoke, and diff hygiene before upload.

The workflow intentionally rejects `v0.1.0` and `v0.1.1` because those tags were
created as GitHub-only releases. Future PyPI uploads must use a strict semver tag whose
version exactly matches `pyproject.toml` and has not already been published.

## Post-Release Verification

After a package release, verify the registry, GitHub Release, publish workflow,
external action smoke, and installed console script from the repository root:

```powershell
$env:RELEASE_VERSION = "0.6.0"
$env:PUBLISH_RUN_ID = "<successful-publish-run-id>"
$env:SMOKE_RUN_ID = "<successful-exact-version-action-smoke-run-id>"
uv run --python 3.12 python scripts/verify_release.py --version $env:RELEASE_VERSION --publish-run-id $env:PUBLISH_RUN_ID --smoke-run-id $env:SMOKE_RUN_ID
```

Set `PUBLISH_RUN_ID` to the successful `Publish PyPI` workflow run for the
matching exact release tag. Do not reuse an older release's run id.
Set `SMOKE_RUN_ID` to the external smoke run that used that same exact version
Action tag. A successful run against `main`, mutable `v0`, another version, or
multiple refs is rejected.

The smoke repository keeps mutable-channel and exact-release workflows
separate. `AI-BOM Smoke` continuously exercises `@v0`, while
`AI-BOM Release Smoke` pins the newest exact version and is the default evidence
source for `scripts/verify_release.py`.

The script checks:

- PyPI project JSON identifies `ai-bom-generator`, and the exact-version JSON
  identifies the requested release even if project-root `latest` metadata is
  still propagating;
- the published version includes both wheel and source distributions;
- `uv run --python 3.12 --with ai-bom-generator==<version> ai-bom --help`
  succeeds outside the source tree;
- the GitHub Release for `v<version>` exists and is not draft or prerelease;
- releases after the explicit pre-enforcement set through `v0.2.0` report
  GitHub-enforced immutability;
- the provided PyPI publish workflow run completed successfully against the
  matching release tag;
- the selected external smoke workflow in
  `0disoft/ai-bom-generator-action-smoke` completed successfully and its
  workflow at the run's exact commit uses only the matching exact-version Action
  ref.

## Mutable Action Tag

`v0` is a convenience ref for users who want compatible 0.x updates without
editing workflow files. Keep exact version tags for release reproducibility;
GitHub enforces immutability for releases after `v0.2.0`.

Only move `v0` after:

- the target exact version tag is published and the corresponding release is
  GitHub-immutable when it is newer than `v0.2.0`;
- the repository CI and package release verification pass;
- an external smoke repository passes against the new `v0` target.

The PyPI publish workflow intentionally triggers only strict
`vMAJOR.MINOR.PATCH` tags, so moving `v0` must not upload a package.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: contract drift, missing fixture evidence, invalid exporter output, or action permission drift blocks release.
- Versioning scheme: `0.1.0` marks the first public MVP; compatible 0.x releases
  use immutable semver tags while the mutable `v0` tag tracks the supported
  action line.
- Rollback: mark a broken GitHub Release in release notes, then publish a patch
  tag after validation. Do not retarget or delete an existing immutable release
  tag.
- Remaining operational risk: marketplace rollout, maintainer escalation path,
  and long-term rollout cadence remain UNDECIDED.
