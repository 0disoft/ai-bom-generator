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
- Artifact pattern, single-file, or total-byte budget hit.
- Unsupported, malformed, partially parsed, or over-budget dependency files.
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
| `EMPTY_MODEL_METADATA` | `[model]` exists without scalar metadata. | CLI empty model metadata warning test |
| `MISSING_ARTIFACT_SELECTION` | No artifact include patterns were declared and discovery was not enabled. | `sparse-project` CLI tests |
| `MISSING_ARTIFACT` | Include pattern or enabled discovery matched no artifact. | `missing-artifact` and artifact discovery CLI tests |
| `ARTIFACT_MATCH_LIMIT_EXCEEDED` | Include pattern matched more candidate paths than the fixed MVP budget allows. | CLI artifact budget tests |
| `ARTIFACT_SIZE_LIMIT_EXCEEDED` | Selected artifact exceeded the fixed MVP single-file byte budget. | CLI artifact budget tests |
| `ARTIFACT_TOTAL_SIZE_LIMIT_EXCEEDED` | Selected artifact would exceed the fixed MVP total artifact byte budget. | CLI artifact budget tests |
| `UNSUPPORTED_DEPENDENCY_FORMAT` | Explicit dependency file uses a format that is not supported for package parsing. | CLI dependency format warning test |
| `DEPENDENCY_PARSE_FAILED` | Supported dependency file is unreadable or invalid as its declared UTF-8, TOML, or bounded YAML format. | CLI invalid uv.lock plus Poetry and conda-lock parser tests |
| `DEPENDENCY_PARSE_PARTIAL` | Supported dependency file contains skipped directives or malformed entries while retaining valid packages. | CLI malformed requirements plus Poetry and conda-lock parser tests |
| `DEPENDENCY_FILE_LIMIT_EXCEEDED` | Dependency file exceeds a fixed byte, logical-line, or package-count safety limit. | Dependency parser and CLI limit tests |
| `SKIPPED_SYMLINK` | Symlink artifact or metadata file skipped. | `symlink-escape` fixture family and CLI model-card symlink tests |
| `MISSING_PROMPTS_REFERENCE_FILE` | Optional prompt file reference could not be read. | `symlink-escape` CLI tests |
| `MISSING_EVALS_REFERENCE_FILE` | Optional eval file reference could not be read. | CLI stale eval/training reference test |
| `MISSING_TRAINING_REFERENCE_FILE` | Optional training file reference could not be read. | CLI stale eval/training reference test |
| `MISSING_DATASET_LICENSE` | Dataset license was absent or blank. | `secret-redaction` and warning-policy tests |
| `UNSUPPORTED_CONFIG_FIELD` | Non-scalar metadata/reference field ignored. | CLI unsupported structured config test |
| `REDACTION_DISABLED` | `--redaction off` was selected. | `secret-redaction` CLI tests |
| `SKIPPED_GIT_SYMLINK` | Git metadata symlink skipped. | CLI Git symlink warning tests; skipped on hosts without symlink support |
| `UNSUPPORTED_GIT_METADATA_FILE` | `.git` file skipped. | CLI Git metadata file warning test |
| `GIT_HEAD_UNREADABLE` | Git HEAD could not be read. | CLI Git HEAD unreadable warning test |
| `GIT_REF_UNRESOLVED` | Symbolic Git ref could not resolve to a commit, including oversized packed refs. | CLI Git ref tests |
| `GIT_HEAD_UNSUPPORTED` | Git HEAD format is unsupported. | CLI Git HEAD unsupported warning test |

## Severity

MVP should start with `warning` and `error`. More severities should wait until
fixtures prove they are useful.

## Review Blockers

- A warning code is introduced without fixture or direct unit-test coverage.
- A warning is emitted only as terminal prose.
- A warning message claims legal, safety, or security conclusions.
