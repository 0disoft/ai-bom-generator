from __future__ import annotations

from contextlib import redirect_stdout
import io
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
            model_properties = {
                str(item["name"]): str(item["value"])
                for item in bom_payload["metadata"]["component"]["properties"]
            }
            self.assertEqual(model_properties["ai-bom:model:model_card"], "MODEL_CARD.md")

    def test_git_head_ref_is_resolved_into_bom_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            commit = "0123456789abcdef0123456789abcdef01234567"
            ref = project / ".git" / "refs" / "heads" / "main"
            ref.parent.mkdir(parents=True)
            (project / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
            ref.write_text(f"{commit}\n", encoding="utf-8", newline="\n")
            bom = work / "out" / "bom.cdx.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "out" / "warnings.json"),
                    "--summary",
                    str(work / "out" / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:git:head"], "ref: refs/heads/main")
            self.assertEqual(model_properties["ai-bom:git:ref"], "refs/heads/main")
            self.assertEqual(model_properties["ai-bom:git:commit"], commit)

    def test_packed_git_ref_is_resolved_into_bom_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            commit = "abcdef0123456789abcdef0123456789abcdef01"
            git_dir = project / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
            (git_dir / "packed-refs").write_text(
                f"# pack-refs with: peeled fully-peeled sorted\n{commit} refs/heads/main\n",
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "out" / "bom.cdx.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "out" / "warnings.json"),
                    "--summary",
                    str(work / "out" / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:git:commit"], commit)

    def test_unresolved_git_ref_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / ".git").mkdir()
            (project / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
            bom = work / "out" / "bom.cdx.json"
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
                    str(work / "out" / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["warnings"][0]["code"], "GIT_REF_UNRESOLVED")
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:git:head"], "ref: refs/heads/main")
            self.assertEqual(model_properties["ai-bom:git:ref"], "refs/heads/main")
            self.assertNotIn("ai-bom:git:commit", model_properties)

    def test_summary_dash_writes_machine_readable_summary_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
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
                        "-",
                    ]
                )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = json.loads(stdout.getvalue())
            self.assertEqual(summary_payload["status"], "success")
            self.assertEqual(summary_payload["bom_path"], bom.as_posix())
            self.assertEqual(summary_payload["warning_report_path"], warnings.as_posix())
            self.assertTrue(bom.exists())
            self.assertTrue(warnings.exists())

    def test_declared_missing_model_card_fails_as_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config_text = config.read_text(encoding="utf-8")
            config.write_text(
                config_text.replace('model_card = "MODEL_CARD.md"', 'model_card = "MISSING.md"'),
                encoding="utf-8",
                newline="\n",
            )

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)

    def test_missing_command_returns_invalid_input(self) -> None:
        code = main([])

        self.assertEqual(code, ExitCode.INVALID_INPUT)

    def test_missing_required_output_flag_returns_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--warning-report",
                    str(work / "warnings.json"),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)

    def test_invalid_choice_returns_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)

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
                    "--redaction",
                    "lenient",
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)

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

    def test_missing_artifact_pattern_reports_warning_without_fabricated_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "missing-artifact", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
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
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            warning_payload = _read_json(warnings)
            bom_payload = _read_json(bom)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["artifact_count"], 0)
            self.assertEqual(summary_payload["warning_count"], 1)
            self.assertEqual(warning_payload["warning_count"], 1)
            self.assertEqual(warning_payload["warnings"][0]["code"], "MISSING_ARTIFACT")
            self.assertEqual(warning_payload["warnings"][0]["object_id"], "models/missing.safetensors")
            self.assertEqual(bom_payload.get("components"), [])

    def test_stable_input_produces_deterministic_bom_and_warning_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            first = _generate_fixture_outputs(work, "first", "complete-project")
            second = _generate_fixture_outputs(work, "second", "complete-project")

            self.assertEqual(
                (first / "bom.json").read_text(encoding="utf-8"),
                (second / "bom.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (first / "warnings.json").read_text(encoding="utf-8"),
                (second / "warnings.json").read_text(encoding="utf-8"),
            )

    def test_warning_policy_fail_returns_policy_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
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
                    str(warnings),
                    "--summary",
                    str(summary),
                    "--warnings",
                    "fail",
                ]
            )

            self.assertEqual(code, ExitCode.WARNING_POLICY_FAILED)
            self.assertTrue(bom.exists())
            self.assertTrue(warnings.exists())
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "failed")
            self.assertEqual(summary_payload["exit_code"], ExitCode.WARNING_POLICY_FAILED)
            self.assertGreater(summary_payload["warning_count"], 0)
            self.assertEqual(_read_json(warnings)["warning_count"], summary_payload["warning_count"])

    def test_unsupported_exporter_format_fails_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--format",
                    "spdx-ai",
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.EXPORTER_FAILURE)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_output_path_inside_target_root_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            target_output = project / "generated" / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(target_output),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(target_output.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_overlapping_output_paths_are_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            output = work / "shared.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(output),
                    "--warning-report",
                    str(output),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(output.exists())
            self.assertFalse(summary.exists())

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
            warnings = work / "warnings.json"
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
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertNotIn("super-secret-token", bom.read_text(encoding="utf-8"))
            self.assertNotIn("super-secret-token", warnings.read_text(encoding="utf-8"))
            self.assertNotIn("super-secret-token", summary.read_text(encoding="utf-8"))
            self.assertIn("token=REDACTED", bom.read_text(encoding="utf-8"))

    def test_secret_shaped_identifiers_are_redacted_from_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "secret-redaction", project)
            config = project / "aibom.toml"
            secret_identifier_dataset = (
                '\n[[datasets]]\n'
                'name = "dataset?token=super-secret-token"\n'
                'uri = "https://example.invalid/public"\n'
            )
            config.write_text(
                config.read_text(encoding="utf-8") + secret_identifier_dataset,
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            for output in (bom, warnings, summary):
                text = output.read_text(encoding="utf-8")
                self.assertNotIn("super-secret-token", text)
                self.assertIn("token=REDACTED", text)

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


def _model_properties(bom_payload: dict[str, object]) -> dict[str, str]:
    metadata = bom_payload["metadata"]
    assert isinstance(metadata, dict)
    component = metadata["component"]
    assert isinstance(component, dict)
    properties = component["properties"]
    assert isinstance(properties, list)
    return {
        str(item["name"]): str(item["value"])
        for item in properties
        if isinstance(item, dict)
    }


def _generate_fixture_outputs(work: Path, name: str, fixture: str) -> Path:
    project = work / f"{name}-project"
    shutil.copytree(FIXTURES / fixture, project)
    out = work / name / "out"
    code = main(
        [
            "generate",
            str(project),
            "--config",
            str(project / "aibom.toml"),
            "--output",
            str(out / "bom.json"),
            "--warning-report",
            str(out / "warnings.json"),
            "--summary",
            str(out / "summary.json"),
        ]
    )
    if code != ExitCode.SUCCESS:
        raise AssertionError(f"fixture generation failed with exit code {code}")
    return out


if __name__ == "__main__":
    unittest.main()
