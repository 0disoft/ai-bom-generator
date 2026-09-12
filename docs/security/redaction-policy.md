# Redaction Policy

## Sensitive configuration warnings

`SENSITIVE_CONFIG_KEY` reports sensitive key names in accepted `model` metadata
and dependency, dataset, prompt, eval, or training reference extensions, including
nested tables and arrays. It shares the redactor's sensitive-key classification.
One warning is emitted per section/reference record, in both redaction modes.
Its location contains only a schema-owned section/index and `<config>`; caller
keys, values, and filenames are never interpolated. Remove credentials from the
configuration. Unknown schema-forbidden sections still fail validation; file
contents are not inspected. Names such as `tokenizer` do not trigger the rule.

Status: Draft
Owner: UNASSIGNED

## Purpose

The tool writes BOMs, warning reports, JSON summaries, and optional hard-failure
reports. Anything copied from a caller project can become a disclosure, so redaction is part of the product
contract, not just terminal polish.

## Default

Strict redaction is the approved CLI default. Redaction off may be useful for
debugging, but it requires explicit user choice and emits a machine-readable
`REDACTION_DISABLED` warning. Terminal error output remains safety-redacted even
when generated artifacts are requested with redaction disabled.

## Secret-Shaped Values

The redaction layer should detect obvious credential forms before output:

- userinfo credentials in any hierarchical `scheme://user:password@host` URI;

- Token-bearing URLs.
- Basic-auth URLs.
- Private key blocks.
- Credentialed Git remotes.
- Common API-token-shaped strings, including GitHub/OpenAI-style API keys.
- Common provider and DevOps token shapes, including AWS access keys, Slack
  tokens, GitLab personal access tokens, Google API keys, Hugging Face tokens,
  GCP OAuth access tokens, Bearer credentials, and JWT-shaped values.
- Values assigned to sensitive config or JSON keys such as `token`, `secret`,
  `password`, `credential`, `authorization`, `api_key`, `access_key`,
  `private_key`, `client_secret`, `refresh_token`, and `id_token`, even when
  the value itself does not match a provider-specific token shape.
- Disabled redaction must be reported as a warning instead of silently producing
  unredacted output.

Strict redaction is a best-effort defense for known provider shapes and
sensitive key names, not proof that arbitrary or newly introduced credential
formats are absent. Callers must not place credentials in declared evidence,
paths, or lockfile locators, and must review generated artifacts before sharing
or uploading them.

## Output Surfaces

- BOM file.
- Warning report.
- JSON summary.
- Hard-failure report. It always uses strict redaction, including when
  `--redaction off` was requested for generated evidence.
- Terminal output. Error messages are safety-redacted even when generated
  artifacts are requested with `--redaction off`, because failures may occur
  before a warning report can be written.
- GitHub Action logs and outputs.

## Review Blockers

- A new output surface bypasses redaction.
- Redaction only covers JSON summary but not BOM output.
- Redaction only covers provider-shaped values and misses sensitive key names.
- A fixture includes real credentials, real private prompts, real private datasets, or real model weights.
