from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ai_bom_generator.cli import main
from ai_bom_generator.collectors.dependency_files import DependencyParseResult, parse_dependency_file
from ai_bom_generator.errors import ExitCode
from ai_bom_generator.security import Redactor


FIXTURE = Path(__file__).parent / "fixtures" / "ml-ecosystem-dependencies"


class MlEcosystemDependencyFixtureTests(unittest.TestCase):
    def test_transformers_uv_lock_preserves_registry_git_and_editable_sources(self) -> None:
        result = parse_dependency_file(
            FIXTURE / "lockfiles" / "transformers" / "uv.lock",
            "lockfiles/transformers/uv.lock",
            "uv",
            Redactor("strict"),
        )

        self.assertEqual(result.skipped_entries, 0)
        self.assertEqual(
            {package.name: package.source_type for package in result.packages},
            {
                "huggingface-hub": "registry",
                "tokenizers": "git",
                "transformers": "registry",
                "transformers-lab": "editable",
            },
        )
        tokenizers = next(package for package in result.packages if package.name == "tokenizers")
        self.assertEqual(
            tokenizers.source_locator,
            "https://example.invalid/tokenizers.git?rev=fixture#0000000",
        )

    def test_pytorch_requirements_preserve_cuda_versions_and_platform_markers(self) -> None:
        result = self._parse_requirements("pytorch-cu128.txt")

        self.assertEqual(result.skipped_entries, 1)
        self.assertEqual(result.first_issue.location if result.first_issue else None, "line:2")
        self.assertEqual(Counter(package.name for package in result.packages), Counter({"torch": 2, "torchvision": 1}))
        linux_torch = next(package for package in result.packages if package.version == "2.7.1+cu128")
        self.assertIn("sys_platform", linux_torch.marker or "")

    def test_onnx_requirements_preserve_ranges_and_markers_without_claiming_versions(self) -> None:
        result = self._parse_requirements("onnx.txt")

        self.assertEqual(result.skipped_entries, 0)
        packages = {package.name: package for package in result.packages}
        self.assertEqual(packages["onnx"].version, "1.18.0")
        self.assertIsNone(packages["onnxruntime-gpu"].version)
        self.assertIn("platform_system", packages["onnxruntime-gpu"].marker or "")
        self.assertIsNone(packages["protobuf"].version)

    def test_gguf_requirements_preserve_extras_and_remote_direct_reference(self) -> None:
        result = self._parse_requirements("gguf.txt")

        self.assertEqual(result.skipped_entries, 0)
        packages = {package.name: package for package in result.packages}
        self.assertEqual(packages["llama-cpp-python"].extras, ("server",))
        self.assertEqual(packages["huggingface-hub"].extras, ("hf-transfer",))
        self.assertEqual(packages["gguf-toolkit"].source_type, "url")
        self.assertEqual(
            packages["gguf-toolkit"].source_locator,
            "https://example.invalid/releases/gguf_toolkit-1.0.0-py3-none-any.whl#sha256=synthetic",
        )

    def test_combined_fixture_exports_all_profiles_to_cyclonedx_and_spdx(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURE, project)

            cyclonedx, cyclonedx_summary = self._generate(project, work, "cyclonedx-json-1.7")
            spdx, spdx_summary = self._generate(project, work, "spdx-ai")

            cyclonedx_libraries = [item for item in cyclonedx["components"] if item["type"] == "library"]
            spdx_packages = [item for item in spdx["@graph"] if item["type"] == "software_Package"]
            self.assertEqual(len(cyclonedx_libraries), 14)
            self.assertEqual(len(spdx_packages), 14)
            self.assertEqual(Counter(item["name"] for item in cyclonedx_libraries)["torch"], 2)
            self.assertEqual(Counter(item["name"] for item in spdx_packages)["torch"], 2)
            self.assertEqual(_warning_codes(cyclonedx_summary), {"DEPENDENCY_PARSE_PARTIAL"})
            self.assertEqual(_warning_codes(spdx_summary), {"DEPENDENCY_PARSE_PARTIAL"})

    def _parse_requirements(self, name: str) -> DependencyParseResult:
        return parse_dependency_file(
            FIXTURE / "requirements" / name,
            f"requirements/{name}",
            "requirements",
            Redactor("strict"),
        )

    def _generate(
        self,
        project: Path,
        work: Path,
        output_format: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        suffix = "spdx" if output_format == "spdx-ai" else "cdx"
        bom = work / f"bom.{suffix}.json"
        summary = work / f"summary.{suffix}.json"
        code = main(
            [
                "generate",
                str(project),
                "--config",
                str(project / "aibom.toml"),
                "--format",
                output_format,
                "--output",
                str(bom),
                "--warning-report",
                str(work / f"warnings.{suffix}.json"),
                "--summary",
                str(summary),
            ]
        )
        self.assertEqual(code, ExitCode.SUCCESS)
        return _read_json(bom), _read_json(summary)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _warning_codes(summary: dict[str, object]) -> set[str]:
    warnings = summary.get("warnings", [])
    if not isinstance(warnings, list):
        raise AssertionError("summary warnings must be a list")
    return {
        str(warning["code"])
        for warning in warnings
        if isinstance(warning, dict) and "code" in warning
    }


if __name__ == "__main__":
    unittest.main()
