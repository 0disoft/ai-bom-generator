# Output Manifest Contract v1 Draft

Status: Draft
Owner: UNASSIGNED

## Purpose

The output manifest is the commit marker for one generated output set. It lets
local automation and the GitHub Action reject stale or interrupted output sets
without guessing from filenames alone.

The executable schema lives at `schemas/aibom-output-manifest-v1.schema.json`.

## Candidate Fields

- `schema_version`
- `generation_id`
- `status`
- `files[].role`
- `files[].path`
- `files[].sha256`
- `files[].size_bytes`

## Semantics

- `generation_id` is a run-unique identifier for one output set.
- `status` is `committed` only after all referenced generated JSON files have
  been staged and replaced.
- `files` contains one entry per generated JSON output file, excluding the
  manifest itself.
- Consumers should verify every expected role by path, size, and SHA-256 digest
  before using summary-derived automation outputs.
- Stable destination-adjacent lock files serialize the final replacement phase
  for writers that share any generated output path, even when their manifest
  paths differ. Locks are acquired in canonical path order, ownership is
  released by the OS when a process exits, and the coordination lock files
  persist so replacing an inode cannot split future lock ownership.
- A handled replacement failure restores the previously committed output set.
  Generation failures before commit leave existing outputs untouched.

## Review Blockers

- Manifest fields change without updating CLI, Action, and fixture contracts.
- A consumer trusts BOM, warning-report, or summary files without matching the
  manifest when transaction-level confidence is required.
- The manifest embeds source file contents or secrets.
