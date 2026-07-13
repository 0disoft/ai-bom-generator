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
        huggingface_hub = next(package for package in result.packages if package.name == "huggingface-hub")
        self.assertEqual(
            tokenizers.source_locator,
            "https://example.invalid/tokenizers.git?rev=fixture#0000000",
        )
        self.assertEqual(tokenizers.package_source.revision, "0000000")
        self.assertEqual(huggingface_hub.package_source.index, "https://pypi.org/simple")
        self.assertEqual(
            {(item.algorithm, item.value) for item in huggingface_hub.package_source.artifact_hashes},
            {("sha256", "synthetic")},
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
        self.assertEqual(
            [(item.algorithm, item.value) for item in packages["gguf-toolkit"].package_source.artifact_hashes],
            [("sha256", "synthetic")],
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
            self.assertEqual(len(cyclonedx_libraries), 19)
            self.assertEqual(len(spdx_packages), 19)
            self.assertEqual(Counter(item["name"] for item in cyclonedx_libraries)["torch"], 2)
            self.assertEqual(Counter(item["name"] for item in spdx_packages)["torch"], 2)
            cyclonedx_properties = next(
                properties
                for item in cyclonedx_libraries
                if item["name"] == "huggingface-hub"
                for properties in ({entry["name"]: entry["value"] for entry in item["properties"]},)
                if "ai-bom:dependency:source-index" in properties
            )
            self.assertEqual(
                cyclonedx_properties["ai-bom:dependency:source-index"],
                "https://pypi.org/simple",
            )
            self.assertEqual(cyclonedx_properties["ai-bom:dependency:artifact:0:hash"], "sha256:synthetic")
            spdx_tokenizers = next(item for item in spdx_packages if item["name"] == "tokenizers")
            self.assertEqual(spdx_tokenizers["aiBom:sourceRevision"], "0000000")
            cyclonedx_pytorch = next(item for item in cyclonedx_libraries if item["name"] == "pytorch")
            pytorch_properties = {item["name"]: item["value"] for item in cyclonedx_pytorch["properties"]}
            self.assertEqual(pytorch_properties["ai-bom:dependency:lockfile-format"], "conda-lock")
            self.assertEqual(
                pytorch_properties["ai-bom:dependency:source-channel"],
                "https://conda.anaconda.org/pytorch",
            )
            self.assertEqual(pytorch_properties["ai-bom:dependency:source-platform"], "linux-64")
            self.assertEqual(pytorch_properties["ai-bom:dependency:artifact:0:hash"], "md5:11111111111111111111111111111111")
            spdx_numpy = [
                item
                for item in spdx_packages
                if item["name"] == "numpy" and item["aiBom:lockfileFormat"] == "conda-lock"
            ]
            self.assertEqual({item["aiBom:sourcePlatform"] for item in spdx_numpy}, {"linux-64", "osx-arm64"})
            self.assertTrue(all(item["aiBom:sourceChannel"] == "conda-forge" for item in spdx_numpy))
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
