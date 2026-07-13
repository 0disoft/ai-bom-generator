from __future__ import annotations

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.cli import main
from ai_bom_generator.errors import CollectorError, ExitCode, ExporterError, InvalidInputError
from ai_bom_generator.validation import validate_with_schema


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
ERROR_SCHEMA = ROOT / "schemas" / "aibom-error-report-v1.schema.json"


class ErrorReportTests(unittest.TestCase):
    def test_success_and_warning_only_runs_remove_stale_error_reports(self) -> None:
        for fixture in ("complete-project", "sparse-project"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                project = work / "project"
                shutil.copytree(FIXTURES / fixture, project)
                error_report = work / "error.json"
                error_report.write_text('{"stale":true}\n', encoding="utf-8", newline="\n")

                code = main(_generate_args(project, work, error_report))

                self.assertEqual(code, ExitCode.SUCCESS)
                self.assertFalse(error_report.exists())

    def test_hard_failures_emit_schema_valid_reports(self) -> None:
        cases = (
            (InvalidInputError("bad config", "config"), ExitCode.INVALID_INPUT, "INVALID_INPUT", "config"),
            (CollectorError("blocked read", "collector"), ExitCode.COLLECTOR_FAILURE, "COLLECTOR_FAILURE", "collector"),
            (ExporterError("bad export", "exporter"), ExitCode.EXPORTER_FAILURE, "EXPORTER_FAILURE", "exporter"),
            (RuntimeError("unexpected failure"), ExitCode.INTERNAL_ERROR, "INTERNAL_ERROR", "internal-error"),
        )
        for error, exit_code, error_code, stage in cases:
            with self.subTest(error_code=error_code), tempfile.TemporaryDirectory() as temp:
                work = Path(temp)
                project = work / "project"
                shutil.copytree(FIXTURES / "complete-project", project)
                error_report = work / "error.json"
                error_report.write_text('{"stale":true}\n', encoding="utf-8", newline="\n")

                with patch("ai_bom_generator.cli.generate_bom", side_effect=error):
                    code = main(_generate_args(project, work, error_report))

                self.assertEqual(code, exit_code)
                payload = _read_json(error_report)
                validate_with_schema(payload, ERROR_SCHEMA, "AI-BOM error report v1")
                self.assertEqual(payload["error"]["code"], error_code)
                self.assertEqual(payload["error"]["stage"], stage)
                self.assertEqual(payload["exit_code"], exit_code)

    def test_argument_parse_failure_can_emit_error_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            error_report = work / "error.json"

            code = main(["generate", str(work), "--error-report", str(error_report)])

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            payload = _read_json(error_report)
            validate_with_schema(payload, ERROR_SCHEMA, "AI-BOM error report v1")
            self.assertEqual(payload["error"]["code"], "INVALID_INPUT")

    def test_error_report_always_applies_strict_secret_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            error_report = work / "error.json"
            secret = "hf_abcdefghijklmnopqrstuvwxyz123456"

            with patch(
                "ai_bom_generator.cli.generate_bom",
                side_effect=ExporterError(f"provider token={secret}", "exporter"),
            ):
                code = main(_generate_args(project, work, error_report) + ["--redaction", "off"])

            self.assertEqual(code, ExitCode.EXPORTER_FAILURE)
            text = error_report.read_text(encoding="utf-8")
            self.assertNotIn(secret, text)
            self.assertIn("REDACTED", text)

    def test_overlapping_error_report_path_is_rejected_without_clobbering_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            output = work / "bom.json"
            output.write_text('{"preserved":true}\n', encoding="utf-8", newline="\n")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                code = main(_generate_args(project, work, output))

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertEqual(output.read_text(encoding="utf-8"), '{"preserved":true}\n')
            self.assertIn("must not overlap", stderr.getvalue())


def _generate_args(project: Path, work: Path, error_report: Path) -> list[str]:
    return [
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
        "--error-report",
        str(error_report),
    ]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
