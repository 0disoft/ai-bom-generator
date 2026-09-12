from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from ai_bom_generator.cli import build_parser, main
from ai_bom_generator.completion import completion_spec, render_completion


def native_bash():
    if sys.platform == "win32":
        git = shutil.which("git")
        candidate = Path(git).parent.parent / "bin" / "bash.exe" if git else None
        return str(candidate) if candidate and candidate.is_file() else None
    return shutil.which("bash")


class CompletionTests(unittest.TestCase):
    def test_spec_uses_parser_flags_and_exporter_registry(self):
        spec = completion_spec(build_parser())
        self.assertIn("--max-scan-entries", spec["generate"]["words"])
        self.assertEqual(spec["generate"]["choices"]["--format"], ["cyclonedx-json-1.7", "spdx-ai"])
        self.assertIn("--config", spec["generate"]["paths"])
        self.assertIn("--max-scan-entries", spec["generate"]["values"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["completion", "bash"]), 0)
        self.assertIn("complete -o default", output.getvalue())

    @unittest.skipUnless(native_bash(), "Native Bash unavailable; WSL launchers are not test shells")
    def test_bash_completes_exporter_enum_in_native_shell(self):
        script = render_completion(build_parser(), "bash")
        script += '\nCOMP_WORDS=(ai-bom generate --format sp); COMP_CWORD=3; _ai_bom_complete; printf "%s\\n" "${COMPREPLY[@]}"\n'
        result = subprocess.run([native_bash(), "--noprofile", "--norc"], input=script, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "spdx-ai")

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 unavailable")
    def test_powershell_completes_warning_enum_in_native_shell(self):
        script = render_completion(build_parser(), "powershell")
        script += "\n(TabExpansion2 'ai-bom generate --warnings f' 28).CompletionMatches | ForEach-Object CompletionText\n"
        result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-Command", script], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "fail")
