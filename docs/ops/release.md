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
Patch releases such as `v0.1.1` remain immutable GitHub Release tags and may be
used directly as GitHub Action refs. Mutable major action tags such as `v0`,
GitHub Marketplace registration, and generated artifact upload are deferred
until explicitly approved.

PyPI package metadata may be prepared before publishing by adding classifiers,
keywords, and project URLs to `pyproject.toml` and validating README rendering
with a package metadata checker.

## PyPI Publishing Policy

The first PyPI publish is approved as a future release activity, but it must not
reuse an already-published GitHub-only tag. Publish the first package from a new
patch tag after the package registry setup is complete.

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
