from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.collectors import dependency_files
from ai_bom_generator.collectors.dependency_files import (
    DependencyFileLimitError,
    DependencyParseError,
    detect_dependency_format,
    parse_dependency_file,
)
from ai_bom_generator.collectors.pipeline import collect_evidence
from ai_bom_generator.config.loader import LoadedConfig
from ai_bom_generator.security import PathPolicy, Redactor


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "ml-ecosystem-dependencies"
    / "lockfiles"
    / "conda"
    / "conda-lock.yml"
)
CORPUS_FIXTURE = Path(__file__).parent / "fixtures" / "conda-lock-corpus" / "official-shapes-v1.yml"


class CondaLockTests(unittest.TestCase):
    def test_official_shape_corpus_preserves_legacy_ordering_and_platform_evidence(self) -> None:
        result = parse_dependency_file(
            CORPUS_FIXTURE,
            "fixtures/conda-lock-corpus/official-shapes-v1.yml",
            "conda-lock",
            Redactor("strict"),
        )

        self.assertEqual(result.skipped_entries, 0)
        self.assertEqual(len(result.packages), 6)

        noarch = [package for package in result.packages if package.name == "synthetic-noarch"]
        self.assertEqual({package.package_source.platform for package in noarch}, {"linux-64", "osx-64"})
        self.assertEqual({package.package_source.channel for package in noarch}, {"conda-forge"})
        self.assertEqual(len({package.identity_key() for package in noarch}), 2)
        self.assertTrue(
            all(
                {item.algorithm for item in package.package_source.artifact_hashes} == {"md5"}
                for package in noarch
            )
        )

        private = next(package for package in result.packages if package.name == "synthetic-private")
        self.assertEqual(
            private.package_source.channel,
            "https://packages.example.invalid/t/$PRIVATE_CHANNEL_TOKEN/ml",
        )
        self.assertEqual(private.package_source.platform, "linux-64")

        defaults = next(package for package in result.packages if package.name == "synthetic-defaults")
        self.assertIsNone(defaults.package_source.channel)
        self.assertEqual(defaults.package_source.platform, "win-64")

        pip_packages = [package for package in result.packages if package.source_type == "pip"]
        self.assertEqual({package.name for package in pip_packages}, {"synthetic-sdist", "synthetic-wheel"})
        self.assertEqual({package.package_source.platform for package in pip_packages}, {"osx-64", "win-64"})
        self.assertTrue(all(package.package_source.channel is None for package in pip_packages))

    def test_detect_dependency_format_accepts_only_unified_conda_lock_names(self) -> None:
        self.assertEqual(detect_dependency_format("custom.yml", "conda-lock"), "conda-lock")
        self.assertEqual(detect_dependency_format("conda-lock.yml", None), "conda-lock")
        self.assertEqual(detect_dependency_format("env.conda-lock.yaml", None), "conda-lock")
        self.assertIsNone(detect_dependency_format("conda-linux-64.lock", None))
        self.assertIsNone(detect_dependency_format("conda-linux-64.lock.yml", None))

    def test_realistic_fixture_preserves_channels_platforms_hashes_and_pip_entries(self) -> None:
        result = parse_dependency_file(
            FIXTURE,
            "lockfiles/conda/conda-lock.yml",
            "conda-lock",
            Redactor("strict"),
        )

        self.assertEqual(result.skipped_entries, 0)
        self.assertEqual(len(result.packages), 5)
        pytorch = next(package for package in result.packages if package.name == "pytorch")
        self.assertEqual(pytorch.source_type, "conda")
        self.assertEqual(pytorch.package_source.channel, "https://conda.anaconda.org/pytorch")
        self.assertEqual(pytorch.package_source.platform, "linux-64")
        self.assertEqual(
            {item.algorithm for item in pytorch.package_source.artifact_hashes},
            {"md5", "sha256"},
        )

        numpy_packages = [package for package in result.packages if package.name == "numpy"]
        self.assertEqual({package.package_source.platform for package in numpy_packages}, {"linux-64", "osx-arm64"})
        self.assertEqual({package.package_source.channel for package in numpy_packages}, {"conda-forge"})
        self.assertEqual(len({package.identity_key() for package in numpy_packages}), 2)

        pip_packages = [package for package in result.packages if package.name == "onnxruntime-gpu"]
        self.assertEqual(len(pip_packages), 2)
        self.assertEqual({package.source_type for package in pip_packages}, {"pip"})
        self.assertEqual({package.package_source.platform for package in pip_packages}, {"linux-64", "osx-arm64"})
        self.assertTrue(all(package.package_source.channel is None for package in pip_packages))

    def test_malformed_package_is_warned_without_fabricated_component(self) -> None:
        payload = _minimal_lock(
            "  - name: valid\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/valid-1.0-0.conda\n"
            '    hash: {md5: "11111111111111111111111111111111"}\n'
            "  - name: fabricated\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: win-64\n"
            "    url: https://example.invalid/fabricated.conda\n"
            '    hash: {md5: "22222222222222222222222222222222"}\n'
            "  - name: numeric-hash\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/numeric-hash-1.0-0.conda\n"
            "    hash: {md5: 33333333333333333333333333333333}\n"
        )

        result = _parse_temp(payload)

        self.assertEqual([package.name for package in result.packages], ["valid"])
        self.assertEqual(result.skipped_entries, 2)
        self.assertEqual(result.first_issue.location if result.first_issue else None, "package[1].platform")

    def test_local_urls_invalid_hashes_and_false_channel_matches_are_not_claimed(self) -> None:
        payload = _minimal_lock(
            "  - name: windows-local\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: 'C:\\weights\\windows-local.conda'\n"
            '    hash: {md5: "11111111111111111111111111111111"}\n'
            "  - name: invalid-hash\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/invalid-hash.conda\n"
            '    hash: {md5: "not-a-real-md5"}\n'
            "  - name: unmatched-channel\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://packages.example.invalid/conda-forge/linux-64/unmatched-channel.conda\n"
            '    hash: {md5: "22222222222222222222222222222222"}\n'
        )

        result = _parse_temp(payload)

        self.assertEqual([package.name for package in result.packages], ["unmatched-channel"])
        self.assertIsNone(result.packages[0].package_source.channel)
        self.assertEqual(result.skipped_entries, 2)

    def test_unsupported_version_duplicate_keys_and_aliases_fail_without_packages(self) -> None:
        payloads = {
            "unsupported-version": _minimal_lock("", version=2),
            "duplicate-key": _minimal_lock("", metadata_suffix="  platforms: [linux-64]\n"),
            "alias": (
                "version: 1\n"
                "metadata: &metadata\n"
                "  channels: [conda-forge]\n"
                "  platforms: [linux-64]\n"
                "  sources: []\n"
                "package: *metadata\n"
            ),
        }
        for label, payload in payloads.items():
            with self.subTest(label=label):
                with self.assertRaises(DependencyParseError):
                    _parse_temp(payload)

    def test_conda_lock_file_and_package_budgets_fail_without_partial_packages(self) -> None:
        payload = _minimal_lock(
            "  - name: first\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/first-1.0-0.conda\n"
            '    hash: {md5: "11111111111111111111111111111111"}\n'
            "  - name: second\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/second-1.0-0.conda\n"
            '    hash: {md5: "22222222222222222222222222222222"}\n'
        )
        with patch.object(dependency_files, "MAX_DEPENDENCY_PACKAGES", 1):
            with self.assertRaises(DependencyFileLimitError):
                _parse_temp(payload)
        with patch.object(dependency_files, "MAX_DEPENDENCY_FILE_BYTES", 4):
            with self.assertRaises(DependencyFileLimitError):
                _parse_temp(payload)

    def test_conda_lock_metadata_budgets_are_enforced(self) -> None:
        cases = (
            ("channels", "channels: [conda-forge, pytorch]", "MAX_CONDA_LOCK_CHANNELS"),
            ("platforms", "platforms: [linux-64, osx-arm64]", "MAX_CONDA_LOCK_PLATFORMS"),
        )
        for label, replacement, limit_name in cases:
            with self.subTest(label=label):
                payload = _minimal_lock("").replace(f"{label}: [{_default_metadata_value(label)}]", replacement)
                with patch.object(dependency_files, limit_name, 1):
                    with self.assertRaises(DependencyFileLimitError):
                        _parse_temp(payload)

    def test_partial_conda_lock_reaches_collector_warning_without_fabricated_package(self) -> None:
        payload = _minimal_lock(
            "  - name: valid\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: https://conda.anaconda.org/conda-forge/linux-64/valid-1.0-0.conda\n"
            '    hash: {md5: "11111111111111111111111111111111"}\n'
            "  - name: invalid\n"
            '    version: "1.0"\n'
            "    manager: conda\n"
            "    platform: linux-64\n"
            "    url: ../invalid.conda\n"
            '    hash: {md5: "22222222222222222222222222222222"}\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "conda-lock.yml").write_text(payload, encoding="utf-8", newline="\n")
            config = LoadedConfig(
                path=None,
                data={"dependencies": [{"path": "conda-lock.yml", "type": "conda-lock"}]},
            )

            evidence = collect_evidence(config, PathPolicy(root), Redactor("strict"))

        self.assertEqual([package.name for package in evidence.dependency_packages], ["valid"])
        dependency_warnings = [warning for warning in evidence.warnings if warning.object_kind == "dependency"]
        self.assertEqual([warning.code for warning in dependency_warnings], ["DEPENDENCY_PARSE_PARTIAL"])

    def test_yaml_nesting_budget_is_enforced(self) -> None:
        nested = "value"
        for _ in range(6):
            nested = f"[{nested}]"
        with patch.object(dependency_files, "MAX_CONDA_LOCK_YAML_DEPTH", 4):
            with self.assertRaises(DependencyParseError):
                _parse_temp(f"version: 1\nmetadata: {nested}\npackage: []\n")


def _minimal_lock(packages: str, *, version: int = 1, metadata_suffix: str = "") -> str:
    return (
        f"version: {version}\n"
        "metadata:\n"
        "  channels: [conda-forge]\n"
        "  platforms: [linux-64]\n"
        "  sources: []\n"
        f"{metadata_suffix}"
        "package:\n"
        f"{packages}"
    )


def _default_metadata_value(label: str) -> str:
    return "conda-forge" if label == "channels" else "linux-64"


def _parse_temp(payload: str):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "conda-lock.yml"
        path.write_text(payload, encoding="utf-8", newline="\n")
        return parse_dependency_file(path, "conda-lock.yml", "conda-lock", Redactor("strict"))


if __name__ == "__main__":
    unittest.main()
