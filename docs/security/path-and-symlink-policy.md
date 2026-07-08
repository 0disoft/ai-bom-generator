# Path and Symlink Policy

Status: Draft
Owner: UNASSIGNED

## Purpose

AI-BOM Generator scans caller-owned local projects. The target directory is
untrusted input and must not be allowed to make the tool read outside the
intended project boundary by default.

## Default Policy

- Resolve the target model directory before collection.
- Treat all user-provided paths and globs as untrusted.
- Block target-root escape by default.
- Do not follow symlinks by default.
- Do not read hidden, ignored, cache, dependency, or build-output paths as source
  truth unless explicitly configured.
- Use explicit artifact include and exclude patterns for large model files.
- Run artifact discovery only when `[artifacts].discovery = true` is explicitly
  configured. Discovery must use built-in excludes for hidden, cache,
  dependency, virtualenv, build, and Git metadata paths.
- Bound artifact include expansion with fixed MVP budgets before hashing:
  256 candidate paths per include pattern after excludes, 16 GiB per artifact,
  and 25 GiB total selected artifact bytes per run.
- Require artifact include and exclude globs to be target-root-relative patterns.
- Reject artifact include and exclude globs that are absolute or contain parent
  traversal.
- Apply recursive exclude globs such as `**/.git/**` and `**/__pycache__/**`
  to target-root-relative artifact paths before hashing.
- Reject generated output paths that resolve inside the target model directory.
- Reject generated output paths that are symlinks, including broken symlinks.
- Reject generated output paths that are existing directories or whose existing
  parent path is not a directory.
- Apply the same generated-output path checks to the generation manifest path.

## Failure Behavior

- Invalid path: invalid-input failure.
- Target-root escape: invalid-input failure or machine-readable warning, depending on whether the path was required.
- Rejected optional reference path: machine-readable warning without emitting
  the rejected path as collected BOM evidence.
- Symlink skipped: machine-readable warning.
- Required artifact inaccessible: collector failure.
- Required artifact changes while hashing: collector failure without emitting
  BOM evidence for a mixed size and digest snapshot.
- Artifact pattern or byte budget hit: machine-readable warning without emitting
  the skipped artifact as collected BOM evidence.
- Unsafe artifact include or exclude glob: invalid-input failure before
  collecting or writing artifacts.
- Generated output path inside the target root: invalid-input failure before
  collecting or writing artifacts.
- Existing output directory or non-directory output parent: invalid-input
  failure before collecting or writing artifacts.

## Review Blockers

- A collector resolves paths independently of the shared path policy.
- A glob can escape the target root.
- A symlink can make the tool read private files outside the target project.
