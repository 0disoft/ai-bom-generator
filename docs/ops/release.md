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

The first public MVP release is `v0.1.0` as an immutable GitHub Release tag.
Patch releases such as `v0.1.2` remain immutable GitHub Release tags and may be
used directly as GitHub Action refs. Mutable major action tags such as `v0`,
GitHub Marketplace registration, and generated artifact upload are deferred
until explicitly approved.

PyPI package metadata may be prepared before publishing by adding classifiers,
keywords, and project URLs to `pyproject.toml` and validating README rendering
with a package metadata checker.

## PyPI Publishing Policy

The first PyPI publish is approved for `v0.1.2`, and it must not reuse an
already-published GitHub-only tag. Publish the first package from a new patch
tag after the package registry setup is complete.

PyPI uploads must use PyPI Trusted Publishing from a GitHub Actions workflow.
Do not commit, document, or rely on long-lived PyPI API tokens for normal
publishing. Before the first upload, the maintainer must:

- create or claim the PyPI project ownership for `ai-bom-generator`;
- configure the matching PyPI trusted publisher for this GitHub repository and
  release workflow;
- recheck package name availability immediately before first publish;
- run the full `VALIDATION.md` check set, including wheel verification and the
  GitHub Action wrapper smoke;
- confirm an external repository smoke has passed against the latest immutable
  GitHub Action tag;
- publish from a new patch tag and mark rollback guidance in the GitHub Release
  notes if the package is broken.

Package registry upload remains blocked until those setup steps are complete.

The prepared publish workflow is `.github/workflows/publish-pypi.yml`. It runs
on strict `vMAJOR.MINOR.PATCH` tags and manual dispatch for an existing tag,
uses the GitHub `pypi` environment, requests job-scoped `id-token: write`, and
publishes with PyPI Trusted Publishing. The workflow rebuilds distributions and
re-runs compile, lint, unit/contract tests, wheel verification, GitHub Action
wrapper smoke, CLI fixture smoke, and diff hygiene before upload.

The workflow intentionally rejects `v0.1.0` and `v0.1.1` because those tags were
created as GitHub-only releases. The first PyPI upload must use `v0.1.2` or a
later patch tag after the PyPI project and trusted publisher are configured.

## Post-Release Verification

After a package release, verify the registry, GitHub Release, publish workflow,
external action smoke, and installed console script from the repository root:

```powershell
uv run --python 3.12 python scripts/verify_release.py --version 0.1.2 --publish-run-id 28930381437
```

The script checks:

- PyPI project JSON and version JSON are live for `ai-bom-generator`;
- the published version includes both wheel and source distributions;
- `uv run --python 3.12 --with ai-bom-generator==<version> ai-bom --help`
  succeeds outside the source tree;
- the immutable GitHub Release for `v<version>` exists and is not draft or
  prerelease;
- the provided PyPI publish workflow run completed successfully against the
  matching release tag;
- the latest external smoke workflow in
  `0disoft/ai-bom-generator-action-smoke` completed successfully.

## Owners

- Primary owner: UNASSIGNED
- Backup owner: UNASSIGNED
- Escalation path: UNDECIDED

## Validation

- Required validation names: VALIDATION.md
- Release blocker status: contract drift, missing fixture evidence, invalid exporter output, or action permission drift blocks release.
- Versioning scheme: `0.1.0` marks the first public MVP; patch releases may use
  `0.1.x` while the MVP contract remains compatible.
- Rollback: mark a broken GitHub Release in release notes, then publish a patch
  tag after validation. Do not retarget or delete an existing immutable release
  tag.
- Remaining operational risk: mutable action tag policy, marketplace rollout,
  maintainer escalation path, and long-term rollout cadence remain UNDECIDED.
