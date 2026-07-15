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
    detect_dependency_format,
    parse_dependency_file,
)
from ai_bom_generator.errors import ExitCode
from ai_bom_generator.security import Redactor


FIXTURE = Path(__file__).parent / "fixtures" / "pipenv-lock"
CORPUS = Path(__file__).parent / "fixtures" / "pipenv-lock-corpus"


class PipenvLockTests(unittest.TestCase):
    def test_detects_exact_pipfile_lock_name_and_declared_aliases(self) -> None:
        self.assertEqual(detect_dependency_format("Pipfile.lock", None), "pipenv")
        self.assertEqual(detect_dependency_format("custom.json", "pipenv"), "pipenv")
        self.assertEqual(detect_dependency_format("custom.json", "pipfile-lock"), "pipenv")
        self.assertIsNone(detect_dependency_format("nested.Pipfile.lock.json", None))

    def test_spec_6_fixture_preserves_sources_hashes_markers_extras_and_refs(self) -> None:
        result = self._parse_fixture()

        self.assertEqual(result.skipped_entries, 0)
        self.assertEqual(len(result.packages), 6)
        packages = {package.name: package for package in result.packages}

        core = packages["synthetic-core"]
        self.assertEqual(core.version, "1.2.3")
        self.assertEqual(core.extras, ("speedups",))
        self.assertEqual(core.marker, "python_version >= '3.12'")
        self.assertEqual(core.source_locator, "https://packages.example.invalid/$PRIVATE_INDEX_TOKEN/simple")
        self.assertEqual(core.package_source.index, core.source_locator)
        self.assertEqual(len(core.package_source.artifact_hashes), 2)

        git = packages["synthetic-git"]
        self.assertIsNone(git.version)
        self.assertEqual(git.source_type, "git")
        self.assertEqual(git.package_source.revision, "abababababababababababababababababababab")

        remote = packages["synthetic-remote-file"]
        self.assertEqual(remote.source_type, "url")
        self.assertEqual(len(remote.package_source.artifact_hashes), 1)

        platform = packages["synthetic-platform"]
        self.assertIsNone(platform.version)
        self.assertEqual(platform.requirement, "synthetic-platform")
        self.assertEqual(platform.marker, "platform_machine == 'x86_64'")

        workspace = packages["synthetic-workspace"]
        self.assertEqual(workspace.source_type, "editable")
        self.assertEqual(workspace.source_locator, "packages/synthetic-workspace")

    def test_fixture_reaches_both_exporters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for output_format in ("cyclonedx-json-1.7", "spdx-ai"):
                suffix = "cdx" if output_format.startswith("cyclonedx") else "spdx"
                bom = work / f"bom.{suffix}.json"
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
                        str(work / f"summary.{suffix}.json"),
                    ]
                )
                self.assertEqual(code, ExitCode.SUCCESS)
                payload = json.loads(bom.read_text(encoding="utf-8"))
                if output_format.startswith("cyclonedx"):
                    packages = [item for item in payload["components"] if item["type"] == "library"]
                    self.assertEqual(len(packages), 6)
                    core = next(item for item in packages if item["name"] == "synthetic-core")
                    properties = {item["name"]: item["value"] for item in core["properties"]}
                    self.assertEqual(properties["ai-bom:dependency:lockfile-format"], "pipenv")
                else:
                    packages = [item for item in payload["@graph"] if item["type"] == "software_Package"]
                    self.assertEqual(len(packages), 6)
                    git = next(item for item in packages if item["name"] == "synthetic-git")
                    self.assertEqual(git["aiBom:sourceRevision"], "abababababababababababababababababababab")

    def test_versioned_corpus_preserves_registry_evidence_across_pipenv_releases(self) -> None:
        normalized_packages: list[list[tuple[object, ...]]] = []

        for producer_version in ("2023.12.1", "2026.6.2"):
            result = self._parse_corpus(producer_version)

            self.assertEqual(result.skipped_entries, 0)
            self.assertEqual([package.name for package in result.packages], ["attrs", "idna"])
            packages = {package.name: package for package in result.packages}

            attrs = packages["attrs"]
            self.assertEqual(attrs.version, "24.2.0")
            self.assertEqual(attrs.marker, "python_version >= '3.8'")
            self.assertEqual(attrs.source_type, "registry")
            self.assertIsNone(attrs.source_locator)
            self.assertEqual(len(attrs.package_source.artifact_hashes), 2)

            idna = packages["idna"]
            self.assertEqual(idna.version, "3.10")
            self.assertEqual(idna.marker, "python_version >= '3.6'")
            self.assertEqual(idna.source_type, "registry")
            self.assertEqual(idna.source_locator, "https://pypi.org/simple")
            self.assertEqual(idna.package_source.index, "https://pypi.org/simple")
            self.assertEqual(len(idna.package_source.artifact_hashes), 2)

            normalized_packages.append(
                [
                    (
                        package.name,
                        package.version,
                        package.requirement,
                        package.marker,
                        package.package_source.identity_key(),
                    )
                    for package in result.packages
                ]
            )

        self.assertEqual(normalized_packages[0], normalized_packages[1])

    def test_malformed_entries_warn_without_fabricated_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Pipfile.lock"
            path.write_text(
                json.dumps(
                    {
                        "_meta": {"pipfile-spec": 6, "sources": []},
                        "default": {
                            "valid-package": {
                                "git": "https://example.invalid/valid.git",
                                "path": ".",
                                "hashes": ["bad"],
                                "markers": 7,
                                "version": "not-a-specifier",
                            },
                            "invalid name!": {"version": "==1.0"},
                        },
                        "develop": {},
                    }
                ),
                encoding="utf-8",
                newline="\n",
            )
            result = parse_dependency_file(path, "Pipfile.lock", "pipenv", Redactor("strict"))

        self.assertEqual(len(result.packages), 1)
        package = result.packages[0]
        self.assertEqual(package.name, "valid-package")
        self.assertIsNone(package.version)
        self.assertEqual(package.source_type, "unknown")
        self.assertIsNone(package.source_locator)
        self.assertIsNone(package.marker)
        self.assertEqual(package.package_source.artifact_hashes, ())
        self.assertGreaterEqual(result.skipped_entries, 5)

    def test_duplicate_keys_unsupported_spec_and_budgets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate = root / "duplicate.lock"
            duplicate.write_text(
                '{"_meta":{"pipfile-spec":6},"default":{},"default":{},"develop":{}}',
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(DependencyParseError):
                parse_dependency_file(duplicate, "Pipfile.lock", "pipenv", Redactor("strict"))

            unsupported = root / "unsupported.lock"
            unsupported.write_text(
                '{"_meta":{"pipfile-spec":7},"default":{},"develop":{}}',
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(DependencyParseError):
                parse_dependency_file(unsupported, "Pipfile.lock", "pipenv", Redactor("strict"))

        with patch.object(dependency_files, "MAX_DEPENDENCY_PACKAGES", 1):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()
        with patch.object(dependency_files, "MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE", 1):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()
        with patch.object(dependency_files, "MAX_PIPENV_SOURCES", 1):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()
        with patch.object(dependency_files, "MAX_PIPENV_JSON_DEPTH", 3):
            with self.assertRaises(DependencyFileLimitError):
                self._parse_fixture()

    def _parse_fixture(self):
        return parse_dependency_file(
            FIXTURE / "Pipfile.lock",
            "Pipfile.lock",
            "pipenv",
            Redactor("strict"),
        )

    def _parse_corpus(self, producer_version: str):
        return parse_dependency_file(
            CORPUS / f"pipenv-{producer_version}.lock",
            "Pipfile.lock",
            "pipenv",
            Redactor("strict"),
        )


if __name__ == "__main__":
    unittest.main()
