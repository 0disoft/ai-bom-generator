from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator import __version__
from ai_bom_generator.cli import main
from ai_bom_generator.errors import CollectorError, ExitCode, ExporterError, InvalidInputError


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
            _assert_manifest_matches_outputs(
                summary.with_name(f"{summary.name}.manifest.json"),
                {
                    "bom": bom,
                    "warning_report": warnings,
                    "summary": summary,
                },
            )
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
            eval_component = next(
                component
                for component in bom_payload["components"]
                if component["bom-ref"] == "eval:smoke-eval"
            )
            eval_properties = {
                str(item["name"]): str(item["value"])
                for item in eval_component["properties"]
            }
            self.assertEqual(eval_properties["ai-bom:artifact"], "evals/result.json")
            self.assertEqual(eval_properties["ai-bom:path"], "evals/result.json")

    def test_aibom_toml_is_discovered_when_config_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "out" / "bom.cdx.json"
            summary = work / "out" / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
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
            self.assertEqual(summary_payload["artifact_count"], 1)
            self.assertEqual(summary_payload["warning_count"], 0)
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:model:name"], "example-model")
            self.assertEqual(model_properties["ai-bom:model:model_card"], "MODEL_CARD.md")
            codes = _warning_codes(summary)
            self.assertNotIn("MISSING_ARTIFACT_SELECTION", codes)
            self.assertNotIn("MISSING_MODEL_METADATA", codes)

    def test_missing_discovered_config_falls_back_to_inline_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            (project / "MODEL_CARD.md").write_text("# Model\n", encoding="utf-8", newline="\n")
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertNotIn("MISSING_MODEL_METADATA", codes)
            self.assertIn("MISSING_ARTIFACT_SELECTION", codes)

    def test_config_discovery_does_not_search_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            parent = work / "parent"
            project = parent / "project"
            project.mkdir(parents=True)
            (project / "MODEL_CARD.md").write_text("# Model\n", encoding="utf-8", newline="\n")
            (parent / "aibom.toml").write_text(
                'schema_version = "1"\n\n[warning_policy]\nmissing_metadata = "fail"\n',
                encoding="utf-8",
                newline="\n",
            )

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)

    def test_explicit_config_overrides_discovered_aibom_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            explicit_config = project / "custom-aibom.toml"
            explicit_config.write_text(
                (project / "aibom.toml").read_text(encoding="utf-8").replace(
                    'format = "cyclonedx-json-1.7"',
                    'format = "spdx-ai"',
                ),
                encoding="utf-8",
                newline="\n",
            )

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(explicit_config),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertEqual(_read_json(work / "summary.json")["format"], "spdx-ai")

    def test_invalid_discovered_config_returns_invalid_input_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "invalid-config", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_discovered_config_symlink_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / "aibom.toml").unlink()
            outside_config = work / "outside-aibom.toml"
            outside_config.write_text('schema_version = "1"\n', encoding="utf-8", newline="\n")
            try:
                os.symlink(outside_config, project / "aibom.toml")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_model_card_symlink_is_warned_and_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            target = work / "outside-model-card.md"
            target.write_text("outside", encoding="utf-8", newline="\n")
            try:
                os.symlink(target, project / "MODEL_CARD.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            bom = work / "bom.json"
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertIn("SKIPPED_SYMLINK", codes)
            self.assertIn("MISSING_MODEL_METADATA", codes)

    def test_broken_model_card_symlink_is_warned(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            try:
                os.symlink(work / "missing-model-card.md", project / "MODEL_CARD.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertIn("SKIPPED_SYMLINK", codes)
            self.assertIn("MISSING_MODEL_METADATA", codes)

    def test_config_output_format_is_used_when_cli_format_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'format = "cyclonedx-json-1.7"',
                    'format = "spdx-ai"',
                ),
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
            self.assertTrue(bom.exists())
            self.assertEqual(_read_json(summary)["format"], "spdx-ai")
            self.assertEqual(_read_json(bom)["aiBom:format"], "spdx-ai")

    def test_complete_project_generates_spdx_ai_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.spdx.json"
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

            self.assertEqual(code, ExitCode.SUCCESS)
            bom_payload = _read_json(bom)
            summary_payload = _read_json(summary)
            graph_by_type = _spdx_graph_by_type(bom_payload)
            model = graph_by_type["ai_AIPackage"][0]
            self.assertEqual(summary_payload["format"], "spdx-ai")
            self.assertEqual(bom_payload["@context"], "https://spdx.org/rdf/3.0.1/spdx-context.jsonld")
            self.assertEqual(bom_payload["aiBom:spdxTarget"], "SPDX 3.0.1 AI Profile preview")
            self.assertEqual(bom_payload["aiBom:conformance"], "partial")
            self.assertEqual(model["name"], "example-model")
            self.assertEqual(model["packageVersion"], "0.1.0")
            self.assertEqual(model["aiBom:modelCard"], "MODEL_CARD.md")
            self.assertIn("releaseTime", model["aiBom:unavailableSpdxAiFields"])
            file_element = graph_by_type["software_File"][0]
            self.assertEqual(file_element["aiBom:path"], "models/model.safetensors")
            self.assertEqual(file_element["verifiedUsing"][0]["algorithm"], "SHA256")
            self.assertRegex(file_element["verifiedUsing"][0]["hashValue"], r"^[0-9a-f]{64}$")
            relationship = graph_by_type["Relationship"][0]
            self.assertEqual(relationship["relationshipType"], "contains")
            self.assertIn(file_element["spdxId"], relationship["to"])

    def test_sparse_project_generates_spdx_ai_preview_with_explicit_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            bom = work / "bom.spdx.json"
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
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertEqual(_read_json(summary)["status"], "success-with-warnings")
            model = _spdx_graph_by_type(_read_json(bom))["ai_AIPackage"][0]
            self.assertEqual(model["name"], "sparse-model")
            self.assertEqual(model["packageVersion"], "NOASSERTION")
            self.assertEqual(
                model["aiBom:unavailableSpdxAiFields"],
                ["suppliedBy", "downloadLocation", "releaseTime"],
            )
            self.assertIn("MISSING_ARTIFACT_SELECTION", _warning_codes(summary))

    def test_cli_output_format_overrides_config_output_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'format = "cyclonedx-json-1.7"',
                    'format = "spdx-ai"',
                ),
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--format",
                    "cyclonedx-json-1.7",
                    "--output",
                    str(work / "bom.json"),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertEqual(_read_json(summary)["format"], "cyclonedx-json-1.7")

    def test_config_output_format_must_be_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'format = "cyclonedx-json-1.7"',
                    'format = 7',
                ),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_config_schema_rejects_invalid_artifact_include_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    "include = [7]",
                ),
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            stderr = io.StringIO()

            with redirect_stderr(stderr):
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertIn("AI-BOM config v1 validation failed", stderr.getvalue())
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

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

    def test_oversized_packed_git_ref_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            git_dir = project / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
            (git_dir / "packed-refs").write_text("x" * (1024 * 1024 + 1), encoding="utf-8", newline="\n")
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
            self.assertIn("GIT_REF_UNRESOLVED", _warning_codes(summary))
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:git:ref"], "refs/heads/main")
            self.assertNotIn("ai-bom:git:commit", model_properties)

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

    def test_git_metadata_file_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / ".git").write_text("gitdir: ../actual.git\n", encoding="utf-8", newline="\n")
            summary = work / "out" / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "out" / "bom.json"),
                    "--warning-report",
                    str(work / "out" / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertIn("UNSUPPORTED_GIT_METADATA_FILE", codes)
            model_properties = _model_properties(_read_json(work / "out" / "bom.json"))
            self.assertNotIn("ai-bom:git:commit", model_properties)

    def test_git_head_unsupported_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / ".git").mkdir()
            (project / ".git" / "HEAD").write_text("not-a-supported-head\n", encoding="utf-8", newline="\n")
            summary = work / "out" / "summary.json"
            bom = work / "out" / "bom.json"

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
            self.assertIn("GIT_HEAD_UNSUPPORTED", _warning_codes(summary))
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:git:head"], "not-a-supported-head")
            self.assertNotIn("ai-bom:git:commit", model_properties)

    def test_git_head_unreadable_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / ".git").mkdir()
            (project / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
            summary = work / "out" / "summary.json"

            with patch("ai_bom_generator.collectors.pipeline._read_git_text_file", side_effect=OSError("blocked")):
                code = main(
                    [
                        "generate",
                        str(project),
                        "--config",
                        str(project / "aibom.toml"),
                        "--output",
                        str(work / "out" / "bom.json"),
                        "--warning-report",
                        str(work / "out" / "warnings.json"),
                        "--summary",
                        str(summary),
                    ]
                )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertIn("GIT_HEAD_UNREADABLE", _warning_codes(summary))

    def test_git_symlink_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            target = work / "external-git"
            target.mkdir()
            try:
                os.symlink(target, project / ".git", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            summary = work / "out" / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--output",
                    str(work / "out" / "bom.json"),
                    "--warning-report",
                    str(work / "out" / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertIn("SKIPPED_GIT_SYMLINK", _warning_codes(summary))

    def test_broken_git_symlink_warns_without_fabricated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            try:
                os.symlink(work / "missing-git-dir", project / ".git", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            summary = work / "out" / "summary.json"
            bom = work / "out" / "bom.json"

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
            self.assertIn("SKIPPED_GIT_SYMLINK", _warning_codes(summary))
            model_properties = _model_properties(_read_json(bom))
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
            _assert_manifest_matches_outputs(
                bom.with_name(f"{bom.name}.manifest.json"),
                {
                    "bom": bom,
                    "warning_report": warnings,
                },
            )

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

    def test_missing_config_schema_version_fails_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace('schema_version = "1"\n\n', ""),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_unsupported_config_schema_version_fails_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace('schema_version = "1"', 'schema_version = "2"'),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_missing_command_returns_invalid_input(self) -> None:
        code = main([])

        self.assertEqual(code, ExitCode.INVALID_INPUT)

    def test_version_returns_package_version_without_requiring_command(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--version"])

        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertEqual(stdout.getvalue(), f"ai-bom-generator {__version__}\n")
        self.assertEqual(stderr.getvalue(), "")

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

    def test_terminal_error_output_redacts_secret_shaped_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            stderr = io.StringIO()

            with redirect_stderr(stderr):
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
                        "--format",
                        "spdx-ai?token=super-secret-token",
                    ]
                )

            self.assertEqual(code, ExitCode.EXPORTER_FAILURE)
            self.assertNotIn("super-secret-token", stderr.getvalue())
            self.assertIn("token=REDACTED", stderr.getvalue())

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

    def test_artifact_discovery_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            (project / "models").mkdir()
            (project / "models" / "auto.safetensors").write_bytes(b"model")
            config = project / "aibom.toml"
            config.write_text(
                'schema_version = "1"\n\n[model]\nname = "discovery-model"\n',
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

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
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["artifact_count"], 0)
            self.assertIn("MISSING_ARTIFACT_SELECTION", _warning_codes(summary))

    def test_artifact_discovery_collects_default_model_artifact_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            (project / "models").mkdir()
            (project / "models" / "auto.safetensors").write_bytes(b"model")
            config = project / "aibom.toml"
            config.write_text(
                'schema_version = "1"\n\n[model]\nname = "discovery-model"\n\n[artifacts]\ndiscovery = true\n',
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
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
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertEqual(_read_json(summary)["artifact_count"], 1)
            self.assertIn("artifact:models/auto.safetensors", _component_refs(_read_json(bom)))

    def test_artifact_discovery_warns_when_no_default_patterns_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            config = project / "aibom.toml"
            config.write_text(
                'schema_version = "1"\n\n[model]\nname = "discovery-model"\n\n[artifacts]\ndiscovery = true\n',
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

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
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["artifact_count"], 0)
            warning = _first_warning(summary_payload, "MISSING_ARTIFACT")
            self.assertEqual(warning["object_id"], "artifacts.discovery")
            self.assertEqual(warning["source"]["field"], "artifacts.discovery")

    def test_artifact_discovery_applies_default_excludes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            (project / "models").mkdir()
            (project / "models" / "auto.safetensors").write_bytes(b"model")
            (project / ".cache").mkdir()
            (project / ".cache" / "hidden.safetensors").write_bytes(b"hidden")
            (project / "build").mkdir()
            (project / "build" / "built.safetensors").write_bytes(b"built")
            config = project / "aibom.toml"
            config.write_text(
                'schema_version = "1"\n\n[model]\nname = "discovery-model"\n\n[artifacts]\ndiscovery = true\n',
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            component_refs = _component_refs(_read_json(bom))
            self.assertIn("artifact:models/auto.safetensors", component_refs)
            self.assertNotIn("artifact:.cache/hidden.safetensors", component_refs)
            self.assertNotIn("artifact:build/built.safetensors", component_refs)

    def test_artifact_discovery_warns_and_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            project.mkdir()
            outside = work / "outside.safetensors"
            outside.write_bytes(b"outside")
            (project / "models").mkdir()
            try:
                os.symlink(outside, project / "models" / "linked.safetensors")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            config = project / "aibom.toml"
            config.write_text(
                'schema_version = "1"\n\n[model]\nname = "discovery-model"\n\n[artifacts]\ndiscovery = true\n',
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
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
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertEqual(_read_json(summary)["artifact_count"], 0)
            self.assertIn("SKIPPED_SYMLINK", _warning_codes(summary))
            self.assertEqual(_component_refs(_read_json(bom)), set())

    def test_artifact_match_limit_warns_and_skips_broad_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    'include = ["**/*"]',
                ),
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"
            warnings = work / "warnings.json"

            with patch("ai_bom_generator.collectors.pipeline._MAX_ARTIFACT_MATCHES_PER_PATTERN", 2):
                code = main(
                    [
                        "generate",
                        str(project),
                        "--config",
                        str(config),
                        "--output",
                        str(work / "bom.json"),
                        "--warning-report",
                        str(warnings),
                        "--summary",
                        str(summary),
                    ]
                )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            warning_payload = _read_json(warnings)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["artifact_count"], 0)
            self.assertIn("ARTIFACT_MATCH_LIMIT_EXCEEDED", _warning_codes(summary))
            warning = _first_warning(summary_payload, "ARTIFACT_MATCH_LIMIT_EXCEEDED")
            self.assertEqual(warning["object_id"], "**/*")
            self.assertIn("2 candidate paths", warning["message"])
            self.assertEqual(warning_payload["warnings"], summary_payload["warnings"])

    def test_artifact_single_file_size_limit_warns_and_skips_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            summary = work / "summary.json"
            warnings = work / "warnings.json"

            with patch("ai_bom_generator.collectors.pipeline._MAX_ARTIFACT_SINGLE_FILE_BYTES", 1):
                code = main(
                    [
                        "generate",
                        str(project),
                        "--config",
                        str(project / "aibom.toml"),
                        "--output",
                        str(work / "bom.json"),
                        "--warning-report",
                        str(warnings),
                        "--summary",
                        str(summary),
                    ]
                )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            warning_payload = _read_json(warnings)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["artifact_count"], 0)
            warning = _first_warning(summary_payload, "ARTIFACT_SIZE_LIMIT_EXCEEDED")
            self.assertEqual(warning["object_id"], "models/model.safetensors")
            self.assertIn("1 byte single-file budget", warning["message"])
            self.assertEqual(warning_payload["warnings"], summary_payload["warnings"])

    def test_artifact_total_size_limit_warns_and_skips_over_budget_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            models = project / "models"
            (models / "a.bin").write_bytes(b"aaa")
            (models / "b.bin").write_bytes(b"bbbb")
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    'include = ["models/*.bin"]',
                ),
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
            summary = work / "summary.json"

            with (
                patch("ai_bom_generator.collectors.pipeline._MAX_ARTIFACT_SINGLE_FILE_BYTES", 10),
                patch("ai_bom_generator.collectors.pipeline._MAX_ARTIFACT_TOTAL_BYTES", 5),
            ):
                code = main(
                    [
                        "generate",
                        str(project),
                        "--config",
                        str(config),
                        "--output",
                        str(bom),
                        "--warning-report",
                        str(work / "warnings.json"),
                        "--summary",
                        str(summary),
                    ]
                )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["artifact_count"], 1)
            warning = _first_warning(summary_payload, "ARTIFACT_TOTAL_SIZE_LIMIT_EXCEEDED")
            self.assertEqual(warning["object_id"], "models/b.bin")
            self.assertIn("5 byte total artifact budget", warning["message"])
            component_refs = _component_refs(_read_json(bom))
            self.assertIn("artifact:models/a.bin", component_refs)
            self.assertNotIn("artifact:models/b.bin", component_refs)

    def test_hash_failure_returns_collector_failure_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            stderr = io.StringIO()

            with (
                patch(
                    "ai_bom_generator.collectors.pipeline.sha256_file_snapshot",
                    side_effect=CollectorError("blocked hash read", "hash"),
                ),
                redirect_stderr(stderr),
            ):
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

            self.assertEqual(code, ExitCode.COLLECTOR_FAILURE)
            self.assertIn("ai-bom: hash: blocked hash read", stderr.getvalue())
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_artifact_change_during_hashing_returns_collector_failure_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            stderr = io.StringIO()
            before = _FakeStat(size=11, modified_ns=100, changed_ns=100)
            after = _FakeStat(size=12, modified_ns=200, changed_ns=200)

            with (
                patch("ai_bom_generator.hashing.sha256.os.fstat", side_effect=[before, after]),
                redirect_stderr(stderr),
            ):
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

            self.assertEqual(code, ExitCode.COLLECTOR_FAILURE)
            self.assertIn("ai-bom: hash: Artifact changed while hashing", stderr.getvalue())
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_unsupported_structured_config_field_reports_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'license_declared = "NOASSERTION"\n\n[[prompts]]',
                    'license_declared = "NOASSERTION"\nannotations = { owner = "team-a" }\n\n[[prompts]]',
                ),
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
            summary_payload = _read_json(summary)
            warning_payload = _read_json(warnings)
            bom_text = bom.read_text(encoding="utf-8")
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["warning_count"], 1)
            self.assertEqual(warning_payload["warnings"][0]["code"], "UNSUPPORTED_CONFIG_FIELD")
            self.assertEqual(warning_payload["warnings"][0]["object_kind"], "dataset")
            self.assertEqual(warning_payload["warnings"][0]["source"]["field"], "datasets[0].annotations")
            self.assertNotIn("team-a", bom_text)
            self.assertNotIn("ai-bom:annotations", bom_text)

    def test_empty_dataset_license_reports_missing_license_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'uri = "https://example.invalid/datasets/example"\nlicense_declared = "NOASSERTION"',
                    'uri = "https://example.invalid/datasets/example"\nlicense_declared = ""',
                ),
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

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
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertIn("MISSING_DATASET_LICENSE", _warning_codes(summary))

    def test_recursive_artifact_excludes_skip_git_and_pycache_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / ".git" / "objects").mkdir(parents=True)
            (project / ".git" / "objects" / "secret-pack").write_text("git metadata", encoding="utf-8", newline="\n")
            (project / "pkg" / "__pycache__").mkdir(parents=True)
            (project / "pkg" / "__pycache__" / "model.pyc").write_bytes(b"cache")
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    'include = ["**/*"]',
                ),
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            component_refs = _component_refs(_read_json(bom))
            self.assertIn("artifact:models/model.safetensors", component_refs)
            self.assertFalse(any(".git/" in ref for ref in component_refs))
            self.assertFalse(any("__pycache__/" in ref for ref in component_refs))

    def test_artifact_include_parent_traversal_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    'include = ["../outside/model.safetensors"]',
                ),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_artifact_exclude_parent_traversal_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'exclude = ["**/.git/**", "**/__pycache__/**"]',
                    'exclude = ["../outside/**"]',
                ),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_artifact_absolute_glob_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    f'include = [{json.dumps((work / "outside.safetensors").as_posix())}]',
                ),
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_stable_input_produces_deterministic_bom_and_warning_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for output_format in ("cyclonedx-json-1.7", "spdx-ai"):
                with self.subTest(output_format=output_format):
                    first = _generate_fixture_outputs(
                        work,
                        f"{output_format}-first",
                        "complete-project",
                        output_format,
                    )
                    second = _generate_fixture_outputs(
                        work,
                        f"{output_format}-second",
                        "complete-project",
                        output_format,
                    )

                    self.assertEqual(
                        (first / "bom.json").read_text(encoding="utf-8"),
                        (second / "bom.json").read_text(encoding="utf-8"),
                    )
                    self.assertEqual(
                        (first / "warnings.json").read_text(encoding="utf-8"),
                        (second / "warnings.json").read_text(encoding="utf-8"),
                    )

    def test_overlapping_artifact_patterns_emit_one_bom_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'include = ["models/model.safetensors"]',
                    'include = ["models/*.safetensors", "models/model.safetensors"]',
                ),
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(config),
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(work / "warnings.json"),
                    "--summary",
                    str(work / "summary.json"),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            components = _read_json(bom)["components"]
            artifact_refs = [
                component["bom-ref"]
                for component in components
                if str(component["bom-ref"]).startswith("artifact:")
            ]
            self.assertEqual(artifact_refs, ["artifact:models/model.safetensors"])
            self.assertEqual(len(artifact_refs), len(set(artifact_refs)))

    def test_duplicate_declared_reference_identity_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8")
                + '\n[[datasets]]\nname = "example-dataset"\nlicense_declared = "NOASSERTION"\n',
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

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

    def test_config_warning_policy_fail_returns_policy_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + '\n[warning_policy]\nmissing_metadata = "fail"\n',
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

            self.assertEqual(code, ExitCode.WARNING_POLICY_FAILED)
            self.assertTrue(bom.exists())
            self.assertTrue(warnings.exists())
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "failed")
            self.assertEqual(summary_payload["exit_code"], ExitCode.WARNING_POLICY_FAILED)
            self.assertGreater(summary_payload["warning_count"], 0)

    def test_cli_warning_policy_overrides_config_warning_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + '\n[warning_policy]\nmissing_metadata = "fail"\n',
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

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
                    str(summary),
                    "--warnings",
                    "allow",
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            summary_payload = _read_json(summary)
            self.assertEqual(summary_payload["status"], "success-with-warnings")
            self.assertEqual(summary_payload["exit_code"], ExitCode.SUCCESS)
            self.assertGreater(summary_payload["warning_count"], 0)

    def test_config_warning_policy_must_be_warn_or_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + '\n[warning_policy]\nmissing_metadata = "block"\n',
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_config_warning_policy_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + '\n[warning_policy]\nmissing_metdata = "fail"\n',
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_config_rejects_unknown_top_level_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + '\n[artifact]\ninclude = ["models/model.safetensors"]\n',
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

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
                    "unsupported-format",
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

    def test_exporter_schema_failure_returns_exporter_failure_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            stderr = io.StringIO()

            with (
                patch(
                    "ai_bom_generator.exporters.cyclonedx_json.mapper.validate_cyclonedx_1_7",
                    side_effect=ExporterError("invalid generated CycloneDX", "exporter"),
                ),
                redirect_stderr(stderr),
            ):
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

            self.assertEqual(code, ExitCode.EXPORTER_FAILURE)
            self.assertIn("ai-bom: exporter: invalid generated CycloneDX", stderr.getvalue())
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_generation_failure_removes_stale_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            manifest = summary.with_name(f"{summary.name}.manifest.json")
            for path in (bom, warnings, summary, manifest):
                path.write_text('{"stale":true}\n', encoding="utf-8", newline="\n")

            code = main(
                [
                    "generate",
                    str(project),
                    "--config",
                    str(project / "aibom.toml"),
                    "--format",
                    "unsupported-format",
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
            self.assertFalse(manifest.exists())

    def test_output_replace_failure_removes_partial_outputs_and_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            warnings = work / "warnings.json"
            summary = work / "summary.json"
            manifest = summary.with_name(f"{summary.name}.manifest.json")
            stderr = io.StringIO()
            real_replace = os.replace
            replace_count = 0

            def flaky_replace(source: Path, destination: Path) -> None:
                nonlocal replace_count
                replace_count += 1
                if replace_count == 2:
                    raise OSError("blocked replace")
                real_replace(source, destination)

            with (
                patch("ai_bom_generator.reporting.json_writer.os.replace", side_effect=flaky_replace),
                redirect_stderr(stderr),
            ):
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

            self.assertEqual(code, ExitCode.INTERNAL_ERROR)
            self.assertIn("ai-bom: internal-error: blocked replace", stderr.getvalue())
            self.assertFalse(bom.exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())
            self.assertFalse(manifest.exists())
            self.assertEqual([], list(work.glob(".*.tmp")))

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

    def test_broken_output_symlink_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "bom.json"
            try:
                os.symlink(work / "missing-output-target.json", bom)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertTrue(bom.is_symlink())
            self.assertFalse((work / "missing-output-target.json").exists())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_existing_directory_output_path_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            bom = work / "existing-output-directory"
            bom.mkdir()
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertTrue(bom.is_dir())
            self.assertFalse(warnings.exists())
            self.assertFalse(summary.exists())

    def test_output_parent_file_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            parent = work / "not-a-directory"
            parent.write_text("occupied", encoding="utf-8", newline="\n")
            bom = parent / "bom.json"
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

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertEqual(parent.read_text(encoding="utf-8"), "occupied")
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

    def test_nested_output_paths_are_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            output = work / "generated"
            warnings = output / "warnings.json"
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
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.INVALID_INPUT)
            self.assertFalse(output.exists())
            self.assertFalse(warnings.exists())
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

    def test_common_provider_secrets_are_redacted_from_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "secret-redaction", project)
            config = project / "aibom.toml"
            aws_key = "AKIA1234567890ABCDEF"
            hf_token = "hf_abcdefghijklmnopqrstuvwxyz123456"
            slack_token = "xoxb-1234567890abcdefghijkl"
            gitlab_token = "glpat-1234567890abcdef"
            google_key = f"AIza{'A' * 35}"
            gcp_token = "ya29.abcdefghijklmnopqrstuvwxyz123456"
            bearer_token = "Bearer abcdefghijklmnop123456"
            jwt_token = "eyJabcdefghijklmno.eyJabcdefghijklmnop.signature1234567890"
            config_text = config.read_text(encoding="utf-8").replace(
                'name = "redaction-model"',
                'name = "redaction-model"\n'
                + f'aws_access_key = "{aws_key}"\n'
                + f'huggingface_token = "{hf_token}"\n'
                + f'google_api_key = "{google_key}"\n'
                + f'gcp_access_token = "{gcp_token}"\n'
                + f'authorization = "{bearer_token}"\n'
                + f'identity_token = "{jwt_token}"',
            )
            config.write_text(
                config_text
                + "\n[[dependencies]]\n"
                + f'name = "{gitlab_token}"\n'
                + 'type = "gitlab"\n'
                + "\n[[datasets]]\n"
                + f'name = "{slack_token}"\n'
                + 'uri = "https://example.invalid/public"\n'
                + 'license_declared = "NOASSERTION"\n',
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
                self.assertNotIn(aws_key, text)
                self.assertNotIn(hf_token, text)
                self.assertNotIn(slack_token, text)
                self.assertNotIn(gitlab_token, text)
                self.assertNotIn(google_key, text)
                self.assertNotIn(gcp_token, text)
                self.assertNotIn("abcdefghijklmnop123456", text)
                self.assertNotIn(jwt_token, text)
            self.assertIn("REDACTED", bom.read_text(encoding="utf-8"))

    def test_key_aware_secret_fields_are_redacted_from_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "secret-redaction", project)
            config = project / "aibom.toml"
            plain_password = "ordinary-looking-password"
            plain_api_key = "ordinary-looking-api-key"
            plain_credential = "ordinary-looking-credential"
            plain_private_key = "ordinary-looking-private-key"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'name = "redaction-model"',
                    'name = "redaction-model"\n'
                    + f'password = "{plain_password}"\n'
                    + f'service_api_key = "{plain_api_key}"\n'
                    + f'credential = "{plain_credential}"\n'
                    + f'private_key = "{plain_private_key}"',
                ),
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
                self.assertNotIn(plain_password, text)
                self.assertNotIn(plain_api_key, text)
                self.assertNotIn(plain_credential, text)
                self.assertNotIn(plain_private_key, text)
            model_properties = _model_properties(_read_json(bom))
            self.assertEqual(model_properties["ai-bom:model:password"], "REDACTED")
            self.assertEqual(model_properties["ai-bom:model:service_api_key"], "REDACTED")
            self.assertEqual(model_properties["ai-bom:model:credential"], "REDACTED")
            self.assertEqual(model_properties["ai-bom:model:private_key"], "REDACTED")

    def test_terminal_error_output_redacts_sensitive_query_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            stderr = io.StringIO()

            with redirect_stderr(stderr):
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
                        "--format",
                        "spdx-ai?password=ordinary-looking-password",
                    ]
                )

            self.assertEqual(code, ExitCode.EXPORTER_FAILURE)
            self.assertNotIn("ordinary-looking-password", stderr.getvalue())
            self.assertIn("password=REDACTED", stderr.getvalue())

    def test_redaction_off_preserves_secret_shaped_values_with_warning(self) -> None:
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
                    "--redaction",
                    "off",
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertIn("super-secret-token", bom.read_text(encoding="utf-8"))
            self.assertNotIn("token=REDACTED", bom.read_text(encoding="utf-8"))
            warning_codes = {str(warning["code"]) for warning in _read_json(summary)["warnings"]}
            self.assertIn("REDACTION_DISABLED", warning_codes)
            self.assertEqual(_read_json(warnings)["warnings"][0]["code"], "REDACTION_DISABLED")
            self.assertEqual(_read_json(summary)["status"], "success-with-warnings")

    def test_empty_model_metadata_reports_machine_readable_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            (project / "MODEL_CARD.md").unlink()
            config = project / "aibom.toml"
            config_text = config.read_text(encoding="utf-8")
            config.write_text(
                config_text.replace(
                    (
                        '[model]\n'
                        'name = "example-model"\n'
                        'version = "0.1.0"\n'
                        'model_card = "MODEL_CARD.md"\n'
                        'license_declared = "NOASSERTION"\n'
                    ),
                    '[model]\naliases = ["example-model"]\n',
                ),
                encoding="utf-8",
                newline="\n",
            )
            summary = work / "summary.json"

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
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertIn("EMPTY_MODEL_METADATA", codes)
            self.assertIn("UNSUPPORTED_CONFIG_FIELD", codes)

    def test_missing_eval_and_training_reference_files_warn_without_fabrication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "complete-project", project)
            config = project / "aibom.toml"
            config.write_text(
                config.read_text(encoding="utf-8")
                + '\n[[evals]]\nname = "stale-eval"\nartifact = "evals/missing.json"\n'
                + '\n[[training]]\nname = "stale-training"\npath = "missing-train.py"\n',
                encoding="utf-8",
                newline="\n",
            )
            bom = work / "bom.json"
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
                    str(work / "warnings.json"),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            codes = _warning_codes(summary)
            self.assertIn("MISSING_EVALS_REFERENCE_FILE", codes)
            self.assertIn("MISSING_TRAINING_REFERENCE_FILE", codes)
            component_refs = _component_refs(_read_json(bom))
            self.assertNotIn("eval:stale-eval", component_refs)
            self.assertNotIn("training:stale-training", component_refs)

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
            bom = work / "bom.json"
            bom_text = bom.read_text(encoding="utf-8")
            self.assertNotIn("../outside.txt", bom_text)
            self.assertNotIn("prompt:outside", _component_refs(_read_json(bom)))

    def test_aibom_error_preserves_exception_args(self) -> None:
        exc = InvalidInputError("bad config", "config")

        self.assertEqual(exc.args, ("bad config",))
        self.assertEqual(str(exc), "bad config")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_manifest_matches_outputs(manifest_path: Path, expected: dict[str, Path]) -> None:
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != "ai-bom-output-manifest/v1":
        raise AssertionError(f"unexpected manifest schema: {manifest.get('schema_version')}")
    if manifest.get("status") != "committed":
        raise AssertionError(f"unexpected manifest status: {manifest.get('status')}")
    generation_id = manifest.get("generation_id")
    if not isinstance(generation_id, str) or not generation_id:
        raise AssertionError(f"unexpected manifest generation_id: {generation_id}")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise AssertionError("manifest files must be a list")
    by_role = {
        str(item.get("role")): item
        for item in files
        if isinstance(item, dict)
    }
    if set(by_role) != set(expected):
        raise AssertionError(f"manifest roles mismatch: {set(by_role)} != {set(expected)}")
    for role, path in expected.items():
        item = by_role[role]
        if item.get("path") != path.as_posix():
            raise AssertionError(f"manifest path mismatch for {role}: {item.get('path')}")
        if item.get("size_bytes") != path.stat().st_size:
            raise AssertionError(f"manifest size mismatch for {role}: {item.get('size_bytes')}")
        if item.get("sha256") != _sha256_file(path):
            raise AssertionError(f"manifest digest mismatch for {role}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _warning_codes(summary_path: Path) -> set[str]:
    return {str(warning["code"]) for warning in _read_json(summary_path)["warnings"]}


def _first_warning(payload: dict[str, object], code: str) -> dict[str, object]:
    warnings = payload["warnings"]
    assert isinstance(warnings, list)
    for warning in warnings:
        if isinstance(warning, dict) and warning.get("code") == code:
            return warning
    raise AssertionError(f"missing warning code: {code}")


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


def _component_refs(bom_payload: dict[str, object]) -> set[str]:
    components = bom_payload["components"]
    assert isinstance(components, list)
    return {
        str(component["bom-ref"])
        for component in components
        if isinstance(component, dict)
    }


def _spdx_graph_by_type(bom_payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    graph = bom_payload["@graph"]
    assert isinstance(graph, list)
    by_type: dict[str, list[dict[str, object]]] = {}
    for element in graph:
        assert isinstance(element, dict)
        by_type.setdefault(str(element["type"]), []).append(element)
    return by_type


def _generate_fixture_outputs(work: Path, name: str, fixture: str, output_format: str) -> Path:
    project = work / f"{name}-project"
    shutil.copytree(FIXTURES / fixture, project)
    out = work / name / "out"
    code = main(
        [
            "generate",
            str(project),
            "--config",
            str(project / "aibom.toml"),
            "--format",
            output_format,
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


class _FakeStat:
    def __init__(self, size: int, modified_ns: int, changed_ns: int) -> None:
        self.st_dev = 1
        self.st_ino = 2
        self.st_size = size
        self.st_mtime_ns = modified_ns
        self.st_ctime_ns = changed_ns


if __name__ == "__main__":
    unittest.main()
