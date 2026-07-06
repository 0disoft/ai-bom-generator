# Repository Design Scaffold

Status: Draft
Scope: data
Repository Type: cli-tool
Addons: github-action

This repository contains an LLM-friendly design scaffold. It is not application source code.

## Source Files

- AGENTS.md: agent working rules
- CHECKLIST.md: checklist router
- VALIDATION.md: validation names and reporting requirements
- .agents/context-map.md: agent route map
- docs/: design, operations, architecture, and engineering standards

## Repository Shape Notes

- cli-tool: This repository type owns command behavior, arguments, flags, config loading, exit codes, terminal output, JSON output, runtime compatibility, and shell integration contracts.
- github-action: This repository type owns action inputs, outputs, permissions, token handling, and runner compatibility.


## Repository Hygiene

.editorconfig, .gitattributes, and .gitignore are generated to keep line endings,
binary diffs, local files, build outputs, caches, and secret files under control.

## Scope Notes

Project-specific implementation choices remain UNDECIDED until the repository owner records them.
