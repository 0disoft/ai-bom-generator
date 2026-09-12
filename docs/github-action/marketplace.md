# Marketplace listing preparation

Status: Maintained guide

## Listing contract

- Name: AI-BOM Generator (availability is checked by GitHub at publication).
- Description: Generate an AI/ML bill of materials with the ai-bom CLI.
- Branding: built-in `package` icon, blue background; no external image asset.
- Primary category: Code quality. Secondary category: Utilities.
- Support: <https://github.com/0disoft/ai-bom-generator/issues> and
  [maintainer policy](../ops/maintainer-policy.md); best effort, no SLA.
- Private security reports:
  <https://github.com/0disoft/ai-bom-generator/security/advisories/new>.
- Privacy: [local-input and privacy decision](../adr/0005-local-input-and-privacy-boundaries.md).
  No product telemetry. GitHub runner logs, tool installation traffic, and
  caller-authorized uploads are separate from product telemetry.

Describe CycloneDX JSON 1.7 and the **partial SPDX 3.0.1 AI preview**. Do not
promise complete provenance, secret-free output, compliance, or vulnerability
assessment. Input/output names are governed by `action.yml` and checked against
[the contract](inputs-and-outputs.md). Artifact uploads are not a built-in
listing feature: use the explicit [caller step](artifact-upload.md).

## Verified installation example

```yaml
permissions:
  contents: read
jobs:
  bom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - id: ai-bom
        uses: 0disoft/ai-bom-generator@v0.6.1
        with:
          model-directory: .
          config: aibom.toml
          warnings: allow
          redaction: strict
```

The target repository supplies its own `aibom.toml` and declared model evidence.
The clean external consumer runs these inputs without preinstalled Python/uv:
[exact release and caller upload smoke](https://github.com/0disoft/ai-bom-generator-action-smoke/actions/runs/34680072291).
The [post-promotion mutable-channel smoke](https://github.com/0disoft/ai-bom-generator-action-smoke/actions/runs/34678929677)
also passed. These links prove 0.6.1, not an unreleased successor.

## Publication and updates

Follow [GitHub's publication procedure](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace):
the owning account reviews/accepts the Marketplace Developer Agreement if
needed, checks name availability, selects categories and an immutable exact
release, and publishes it. This document does not assert agreement acceptance
or a live Marketplace listing. A release being public is not listing evidence.

For each update, require source CI and CodeQL, publish the immutable exact
release, run the clean external exact-version smoke, then promote `v0` and run
its consumer smoke. Update listing instructions only to that verified release.
The listing must never silently claim capabilities from unreleased `main`.
Rollback changes caller pins or the mutable channel only after verifying the
previous exact release; never rewrite immutable tags or delete package files.
