# Shell Completion

Status: Accepted
Repository Type: cli-tool

## Purpose

Shell completion should help users discover stable commands, flags, and enum
values without implying that arbitrary file discovery is safe or complete.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Completion Boundary

- Complete command names and stable flag names after the CLI contract is implemented.
- Complete supported exporter names from the implemented exporter registry.
- Do not auto-complete secrets, tokens, private URLs, or dataset contents.
- File path completion should be delegated to the shell when possible.

## Supported Shells and Installation

Bash and PowerShell 7 are supported. Registrations are generated on demand from
the installed argparse definitions and exporter set; no duplicate flag assets
are shipped. Other shells are rejected with the normal invalid-input exit code.

In Bash, evaluate the locally installed generator's output:

```bash
source <(ai-bom completion bash)
```

In PowerShell 7:

```powershell
ai-bom completion powershell | Out-String | Invoke-Expression
```

These are manual shell registration examples, not project verification commands.
Add the registration to your shell profile for persistence. Regenerate after
upgrading the CLI. Remove the profile line to uninstall; Bash can immediately
unregister using `complete -r ai-bom`, while PowerShell users start a new session.
An empty prefix lists known commands/options; enum completion uses separated
option/value words. Numeric limits offer no value suggestions. File paths are
left to the shell; the generator does not traverse model directories or read
config. It does not make network requests. Only evaluate output from the CLI
installation you trust, not scripts pasted from generated BOMs or project inputs.

Wheel verification executes both completion-generation commands after installation.
Native Bash and PowerShell tests check enum completion when the shell is available;
the hosted Linux environment exercises Bash and locally available PowerShell 7.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
