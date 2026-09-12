"""Generate offline shell registrations from the executable argparse surface."""
import argparse
import json
from pathlib import Path
import shlex

from ai_bom_generator.app import _SUPPORTED_EXPORT_FORMATS


def completion_spec(parser: argparse.ArgumentParser) -> dict:
    result = {}

    def visit(command, current):
        flags, choices, paths = [], {}, []
        for action in current._actions:
            flags.extend(action.option_strings)
            if action.dest == "output_format":
                choices["--format"] = sorted(_SUPPORTED_EXPORT_FORMATS)
            if action.choices is not None and not isinstance(action, argparse._SubParsersAction):
                for flag in action.option_strings:
                    choices[flag] = list(action.choices)
            if action.type is Path:
                paths.extend(action.option_strings)
            if isinstance(action, argparse._SubParsersAction):
                flags.extend(action.choices)
                for name, child in action.choices.items():
                    visit(name, child)
        result[command] = {"words": sorted(set(flags)), "choices": choices, "paths": paths}

    visit("root", parser)
    return result


def render_completion(parser: argparse.ArgumentParser, shell: str) -> str:
    spec = completion_spec(parser)
    if shell == "bash":
        lines = ["_ai_bom_complete() {", '  local cmd="${COMP_WORDS[1]}" cur="${COMP_WORDS[COMP_CWORD]}" prev="${COMP_WORDS[COMP_CWORD-1]}"',
                 "  COMPREPLY=()", '  if (( COMP_CWORD == 1 )); then cmd=root; fi', '  case "$cmd:$prev" in']
        for command, entry in spec.items():
            for flag, values in entry["choices"].items():
                lines.append(f"    {command}:{flag}) COMPREPLY=( $(compgen -W {shlex.quote(' '.join(values))} -- \"$cur\") ); return ;;")
            for flag in entry["paths"]:
                lines.append(f"    {command}:{flag}) compopt -o default 2>/dev/null; return ;;")
        lines += ["  esac", '  case "$cmd" in']
        for command, entry in spec.items():
            if command != "root":
                words = "bash powershell" if command == "completion" else " ".join(entry["words"])
                lines.append(f"    {command}) COMPREPLY=( $(compgen -W {shlex.quote(words)} -- \"$cur\") ) ;;")
        lines += [f"    *) COMPREPLY=( $(compgen -W {shlex.quote(' '.join(spec['root']['words']))} -- \"$cur\") ) ;;", "  esac", "}",
                  "complete -o default -F _ai_bom_complete ai-bom"]
        return "\n".join(lines) + "\n"
    if shell == "powershell":
        data = json.dumps(spec).replace("'", "''")
        return """Register-ArgumentCompleter -Native -CommandName ai-bom -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $parts = @($commandAst.CommandElements | ForEach-Object { $_.Extent.Text })
    $table = ConvertFrom-Json -AsHashtable '""" + data + """'
    $command = if ($parts.Count -gt 1 -and $table.ContainsKey($parts[1])) { $parts[1] } else { 'root' }
    $entry = $table[$command]
    $before = @($commandAst.CommandElements | Where-Object { $_.Extent.EndOffset -lt $cursorPosition -and $_.Extent.Text -ne $wordToComplete })
    $previous = if ($before.Count) { $before[-1].Extent.Text } else { '' }
    if ($entry.paths -contains $previous) { return }
    $words = if ($entry.choices.ContainsKey($previous)) { $entry.choices[$previous] }
             elseif ($command -eq 'completion') { @('bash', 'powershell') }
             else { $entry.words }
    foreach ($candidate in $words) {
        if ($candidate.StartsWith($wordToComplete, [System.StringComparison]::OrdinalIgnoreCase)) {
            [System.Management.Automation.CompletionResult]::new($candidate, $candidate, 'ParameterValue', $candidate)
        }
    }
}
"""
    raise ValueError(f"Unsupported completion shell: {shell}")
