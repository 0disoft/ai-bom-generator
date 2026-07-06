# Warning Taxonomy v1 Draft

Status: Draft
Owner: UNASSIGNED

## Purpose

Warnings are machine-readable evidence gaps. They must be precise enough for CI
policy while staying small enough that users do not ignore them.

## Warning Shape

- `code`
- `severity`
- `object_kind`
- `object_id`
- `source.path`
- `source.field`
- `message`
- `remediation`

## Candidate Categories

- Missing model metadata.
- Missing model artifact digest.
- Missing dataset license declaration.
- Missing dataset source or version.
- Missing prompt reference digest.
- Missing eval reference.
- Unsupported lockfile type.
- Unsupported exporter field.
- Redacted secret-shaped value.
- Skipped symlink.
- Target-root escape blocked.

## Severity

MVP should start with `warning` and `error`. More severities should wait until
fixtures prove they are useful.

## Review Blockers

- A warning code is introduced without a fixture.
- A warning is emitted only as terminal prose.
- A warning message claims legal, safety, or security conclusions.
