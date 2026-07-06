from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ai_bom_generator.cli import main
from ai_bom_generator.errors import ExitCode


FIXTURES = Path(__file__).parent / "fixtures"


class CliTests(unittest.TestCase):
    def test_complete_project_generates_bom_summary_and_warning_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "out" / "bom.cdx.json"
            warnings = work / "out" / "warnings.json"
            summary = work / "out" / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            warning_payload = _read_json(warnings)
            bom_payload = _read_json(bom)
            self.assertEqual(summary_payload["status"], "success")
            self.assertEqual(summary_payload["warning_count"], 0)
            self.assertEqual(warning_payload["warning_count"], 0)
            self.assertEqual(bom_payload["bomFormat"], "CycloneDX")
            self.assertEqual(bom_payload["specVersion"], "1.7")

    def test_sparse_project_reports_machine_readable_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["warnings"][0]["code"], "MISSING_ARTIFACT_SELECTION")

    def test_warning_policy_fail_returns_policy_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                    "--warnings",
                    "fail",
                ]
            )

            self.assertEqual(code, ExitCode.WARNING_POLICY_FAILED)

    def test_invalid_config_returns_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "invalid-config", project)

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)

    def test_secret_shaped_values_are_redacted_from_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "secret-redaction", project)
            bom = work / "bom.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertNotIn("super-secret-token", bom.read_text(encoding="utf-8"))
            self.assertNotIn("super-secret-token", summary.read_text(encoding="utf-8"))
            self.assertIn("token=REDACTED", bom.read_text(encoding="utf-8"))

    def test_target_root_escape_is_reported_for_optional_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "symlink-escape", project)
            (work / "outside.txt").write_text("outside", encoding="utf-8")
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            warnings = _read_json(summary)["warnings"]
            codes = {str(warning["code"]) for warning in warnings}
            self.assertIn("MISSING_PROMPTS_REFERENCE_FILE", codes)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
