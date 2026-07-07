# Warning Taxonomy v1 Draft

Status: Draft
Owner: UNASSIGNED

## Purpose

Warnings are machine-readable evidence gaps. They must be precise enough for CI
policy while staying small enough that users do not ignore them.

The executable warning-report schema lives at
`schemas/aibom-warning-report-v1.schema.json`.

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
- Missing model artifact selection or matched artifact.
- Missing dataset license declaration.
- Missing optional prompt, eval, or training reference files.
- Unsupported config field.
- Unsupported or unresolved local Git metadata.
- Disabled redaction mode.
- Skipped symlink.

## Implemented Warning Codes

| Code | Category | Fixture or test coverage |
| --- | --- | --- |
| `MISSING_MODEL_METADATA` | No `[model]` metadata was declared. | `sparse-project` CLI tests |
| `EMPTY_MODEL_METADATA` | `[model]` exists without scalar metadata. | Covered by collector warning path; add a fixture before changing behavior |
| `MISSING_ARTIFACT_SELECTION` | No artifact include patterns were declared. | `sparse-project` CLI tests |
| `MISSING_ARTIFACT` | Include pattern matched no artifact. | `missing-artifact` CLI tests |
| `SKIPPED_SYMLINK` | Symlink artifact skipped. | `symlink-escape` fixture family |
| `MISSING_PROMPTS_REFERENCE_FILE` | Optional prompt file reference could not be read. | `symlink-escape` CLI tests |
| `MISSING_EVALS_REFERENCE_FILE` | Optional eval file reference could not be read. | Add fixture before changing behavior |
| `MISSING_TRAINING_REFERENCE_FILE` | Optional training file reference could not be read. | Add fixture before changing behavior |
| `MISSING_DATASET_LICENSE` | Dataset license was not declared. | `secret-redaction` and warning-policy tests |
| `UNSUPPORTED_CONFIG_FIELD` | Non-scalar metadata/reference field ignored. | CLI unsupported structured config test |
| `REDACTION_DISABLED` | `--redaction off` was selected. | `secret-redaction` CLI tests |
| `SKIPPED_GIT_SYMLINK` | Git metadata symlink skipped. | Add fixture before changing behavior |
| `UNSUPPORTED_GIT_METADATA_FILE` | `.git` file skipped. | Add fixture before changing behavior |
| `GIT_HEAD_UNREADABLE` | Git HEAD could not be read. | Add fixture before changing behavior |
| `GIT_REF_UNRESOLVED` | Symbolic Git ref could not resolve to a commit. | CLI Git ref tests |
| `GIT_HEAD_UNSUPPORTED` | Git HEAD format is unsupported. | Add fixture before changing behavior |

## Severity

MVP should start with `warning` and `error`. More severities should wait until
fixtures prove they are useful.

## Review Blockers

- A warning code is introduced without fixture or direct unit-test coverage.
- A warning is emitted only as terminal prose.
- A warning message claims legal, safety, or security conclusions.
