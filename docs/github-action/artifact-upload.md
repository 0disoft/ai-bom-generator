# Caller-Owned Artifact Upload

Status: Accepted

Artifact upload belongs in an explicit caller step. The composite Action keeps
read-only permissions and never uploads automatically. No companion Action is
needed: callers can use their chosen storage provider and retention policy.

For GitHub-hosted artifacts, this example opts in to a seven-day retention window.
The caller should review the generated evidence and choose a shorter window when
appropriate. Keep the generation and upload steps adjacent and do not modify
the output files between them. The generator publishes summary status only after
verifying all output sizes and hashes against the current-run manifest.

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v7
  - id: bom
    uses: 0disoft/ai-bom-generator@v0.6.1
    with:
      model-directory: .
      warnings: allow
      redaction: strict
  - name: Upload verified evidence
    if: >-
      success() && steps.bom.outputs.exit-code == '0' &&
      (steps.bom.outputs.status == 'success' ||
       steps.bom.outputs.status == 'success-with-warnings')
    uses: actions/upload-artifact@v4
    with:
      name: ai-bom-${{ github.run_id }}-${{ github.run_attempt }}
      path: |
        ${{ steps.bom.outputs.bom-path }}
        ${{ steps.bom.outputs.warning-report-path }}
        ${{ steps.bom.outputs.summary-path }}
        ${{ steps.bom.outputs.manifest-path }}
      if-no-files-found: error
      retention-days: 7
```

Use default run-unique output destinations for this workflow. Do not use `always()`
to upload successful evidence after a failed generation: previous committed files
may intentionally remain on disk. Error reports are separate private diagnostics,
not part of this success upload. Never upload directories or lock files wholesale.
Redaction remains best effort; `redaction: off` output is unsuitable for automatic
sharing. GitHub artifact visibility follows repository access, not an additional
privacy guarantee from the generator. Forked PR contents remain untrusted input.

Upload failures fail the caller step; they do not undo local generation. The
caller owns retries, artifact deletion, repository access, storage quotas, and
retention settings. A retry should use a distinct run attempt name. GitHub
Enterprise Server users must choose their platform-supported upload mechanism.

Rollback is removal of the caller upload step or deletion of its hosted artifact.
No generator state migration or permission expansion is involved.
