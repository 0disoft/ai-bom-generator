# Documentation

Status: Maintained guide

## Source of Truth

- Product scope source: docs/product/02-spec.md
- Architecture decisions source: docs/adr/*.md
- Data pipeline source: docs/data/pipeline-contract.md
- Operational standard source: docs/ops/00-operational-contract.md
- Validation source: VALIDATION.md
- Agent routing source: .agents/context-map.md
- Repository hygiene source: .editorconfig, .gitattributes, .gitignore
- CLI command contract source: docs/cli/command-contract.md
- CLI output and exit-code source: docs/cli/output-and-exit-codes.md
- Output manifest contract: docs/contracts/output-manifest-v1.md
- Error report contract: docs/contracts/error-report-v1.md
- CLI config source: docs/cli/configuration.md
- GitHub Action source: docs/github-action/README.md
- Exporter mapping notes: docs/exporters/*.md
- Public contracts: docs/contracts/*.md
- Security guidance: docs/security/*.md
- Fixture strategy: docs/testing/fixture-matrix.md

## Document roles and ownership

`document-status.json` inventories every tracked Markdown document outside
generated LLMNav state. Normative contracts were checked against executable
schemas, CLI/Action behavior and the v0.7.0 test/CI evidence. Maintained guides
explain those contracts but do not approve future product decisions. Release
notes remain historical, the ADR template remains a template, and the SPDX
mapping follow-up remains a visibly unresolved proposal until its upstream gate
proves the stronger mapping. Accepted preview documentation is not a full SPDX
conformance claim.

Ownership for all maintained documents follows
[maintainer policy](ops/maintainer-policy.md); per-file unassigned placeholders
have been removed rather than creating fictitious owners. The documentation
contract tests check inventory coverage, roles, schema-required fields, format
names, Action input/output names, and package version agreement. They cannot
prove every prose claim; behavior changes still require focused review.
