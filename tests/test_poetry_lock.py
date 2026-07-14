from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.cli import main
from ai_bom_generator.collectors import dependency_files
from ai_bom_generator.collectors.dependency_files import (
    DependencyFileLimitError,
    DependencyParseError,
    DependencyParseResult,
    detect_dependency_format,
    parse_dependency_file,
)
from ai_bom_generator.errors import ExitCode
from ai_bom_generator.security import Redactor


FIXTURE = Path(__file__).parent / "fixtures" / "poetry-lock"
CORPUS = Path(__file__).parent / "fixtures" / "poetry-lock-corpus"


class PoetryLockTests(unittest.TestCase):
    def test_detects_exact_poetry_lock_name_and_declared_type(self) -> None:
        self.assertEqual(detect_dependency_format("poetry.lock", None), "poetry")
        self.assertEqual(detect_dependency_format("custom.toml", "poetry"), "poetry")
        self.assertEqual(detect_dependency_format("custom.toml", "poetry-lock"), "poetry")
        self.assertIsNone(detect_dependency_format("nested.poetry.lock", None))

    def test_poetry_2_fixture_preserves_markers_sources_revisions_and_file_hashes(self) -> None:
        result = self._parse_fixture()

        self.assertEqual(result.skipped_entries, 1)
        self.assertEqual(len(result.packages), 5)
        packages = {package.name: package for package in result.packages}

        registry = packages["synthetic-array"]
        self.assertEqual(registry.source_type, "registry")
        self.assertIn("python_version", registry.marker or "")
        self.assertEqual(
            {item.locator for item in registry.package_source.artifact_hashes},
            {"synthetic_array-2.2.0-py3-none-any.whl", "synthetic_array-2.2.0.tar.gz"},
        )

        git = packages["synthetic-git"]
        self.assertEqual(git.source_locator, "https://example.invalid/synthetic-git.git")
        self.assertEqual(git.package_source.revision, "0000000000000000000000000000000000000000")

        private = packages["synthetic-private"]
        self.assertEqual(private.source_type, "legacy")
        self.assertIsNone(private.marker)
        self.assertEqual(
            private.package_source.index,
            "https://packages.example.invalid/$PRIVATE_INDEX_TOKEN/simple",
        )

        local = packages["synthetic-local"]
        self.assertEqual(local.source_type, "directory")
        self.assertEqual(local.source_locator, "packages/synthetic-local")

        direct = packages["synthetic-direct"]
        self.assertEqual(direct.source_type, "url")
        self.assertIn("sys_platform", direct.marker or "")

    def test_poetry_2_0_corpus_preserves_category_era_sources_and_hashes(self) -> None:
        result = self._parse_corpus("poetry-2.0.lock")

        self.assertEqual(result.skipped_entries, 0)
        self.assertEqual(
            [package.name for package in result.packages],
            ["synthetic-core", "synthetic-git-20", "synthetic-legacy-index"],
        )
        packages = {package.name: package for package in result.packages}

        core = packages["synthetic-core"]
        self.assertEqual(core.source_type, "registry")
        self.assertEqual(
            [(item.algorithm, item.locator) for item in core.package_source.artifact_hashes],
            [("sha256", "synthetic_core-1.3.0-py3-none-any.whl")],
        )
        legacy = packages["synthetic-legacy-index"]
        self.assertEqual(legacy.source_type, "legacy")
        self.assertEqual(legacy.package_source.index, "https://packages.example.invalid/simple")
        git = packages["synthetic-git-20"]
        self.assertEqual(git.package_source.revision, "2020202020202020202020202020202020202020")

        for package in result.packages:
            self.assertIsNone(package.marker)
            self.assertEqual(package.extras, ())

    def test_poetry_2_1_corpus_handles_group_marker_shapes_without_inference(self) -> None:
        result = self._parse_corpus("poetry-2.1.lock")

        self.assertEqual(result.skipped_entries, 1)
        self.assertEqual(len(result.packages), 4)
        packages = {package.name: package for package in result.packages}

        shared = packages["synthetic-shared-marker"]
        self.assertEqual(shared.marker, "python_version >= '3.10'")
        self.assertEqual(shared.extras, ())
        split = packages["synthetic-split-marker"]
        self.assertIsNone(split.marker)
        self.assertEqual(split.extras, ())
        direct = packages["synthetic-url-21"]
        self.assertEqual(direct.source_type, "url")
        self.assertEqual(
            [item.locator for item in direct.package_source.artifact_hashes],
            ["synthetic_url_21-4.0.0-py3-none-any.whl"],
        )
        git = packages["synthetic-git-21"]
        self.assertEqual(git.package_source.revision, "5151515151515151515151515151515151515151")
        self.assertEqual(git.source_locator, "https://example.invalid/synthetic-git-21.git")

        self.assertIsNotNone(result.first_issue)
        assert result.first_issue is not None
        self.assertEqual(result.first_issue.location, "package[1].markers")
        self.assertIn("selected group", result.first_issue.reason)

    def test_poetry_fixture_reaches_both_exporters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for output_format in ("cyclonedx-json-1.7", "spdx-ai"):
                suffix = "cdx" if output_format.startswith("cyclonedx") else "spdx"
                bom = work / f"bom.{suffix}.json"
                summary = work / f"summary.{suffix}.json"
                code = main(
                    [
                        "generate",
                        str(FIXTURE),
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
                payload = json.loads(bom.read_text(encoding="utf-8"))
                summary_payload = json.loads(summary.read_text(encoding="utf-8"))
                warning_codes = {
                    warning["code"]
                    for warning in summary_payload["warnings"]
                    if isinstance(warning, dict) and "code" in warning
                }
                self.assertIn("DEPENDENCY_PARSE_PARTIAL", warning_codes)
                if output_format.startswith("cyclonedx"):
                    packages = [item for item in payload["components"] if item["type"] == "library"]
                    self.assertEqual(len(packages), 5)
                    private = next(item for item in packages if item["name"] == "synthetic-private")
                    properties = {item["name"]: item["value"] for item in private["properties"]}
                    self.assertEqual(properties["ai-bom:dependency:lockfile-format"], "poetry")
                    self.assertIn("PRIVATE_INDEX_TOKEN", properties["ai-bom:dependency:source-index"])
                else:
                    packages = [item for item in payload["@graph"] if item["type"] == "software_Package"]
                    self.assertEqual(len(packages), 5)
                    git = next(item for item in packages if item["name"] == "synthetic-git")
                    self.assertEqual(git["aiBom:sourceRevision"], "0" * 40)

    def test_invalid_major_and_malformed_entries_do_not_fabricate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unsupported = root / "unsupported.lock"
            unsupported.write_text(
                '[[package]]\nname = "example"\nversion = "1.0"\n\n'
                '[metadata]\nlock-version = "1.1"\n',
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(DependencyParseError):
                parse_dependency_file(unsupported, "poetry.lock", "poetry", Redactor("strict"))

            partial = root / "partial.lock"
            partial.write_text(
                '[[package]]\nname = "Valid_Name"\nversion = "1.0"\n'
                'markers = 7\nfiles = [{file = "valid.whl", hash = "bad"}]\n'
                'source = {type = "mystery", url = "https://example.invalid/simple"}\n\n'
                '[[package]]\nname = 7\nversion = "2.0"\n\n'
                '[metadata]\nlock-version = "2.1"\n',
                encoding="utf-8",
                newline="\n",
            )
            result = parse_dependency_file(partial, "poetry.lock", "poetry", Redactor("strict"))

        self.assertEqual(len(result.packages), 1)
        self.assertEqual(result.packages[0].name, "valid-name")
        self.assertEqual(result.packages[0].source_type, "unknown")
        self.assertIsNone(result.packages[0].marker)
        self.assertEqual(result.packages[0].package_source.artifact_hashes, ())
        self.assertGreaterEqual(result.skipped_entries, 4)

    def test_package_and_file_budgets_remain_facade_controlled(self) -> None:
        with patch.object(dependency_files, "MAX_DEPENDENCY_PACKAGES", 1):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()
        with patch.object(dependency_files, "MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE", 1):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()

    def _parse_fixture(self) -> DependencyParseResult:
        return parse_dependency_file(
            FIXTURE / "poetry.lock",
            "poetry.lock",
            "poetry",
            Redactor("strict"),
        )

    def _parse_corpus(self, name: str) -> DependencyParseResult:
        return parse_dependency_file(
            CORPUS / name,
            "poetry.lock",
            "poetry",
            Redactor("strict"),
        )


if __name__ == "__main__":
    unittest.main()
