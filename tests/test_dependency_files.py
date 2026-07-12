from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.collectors import dependency_files
from ai_bom_generator.collectors.dependency_files import (
    DependencyFileLimitError,
    detect_dependency_format,
    parse_dependency_file,
)
from ai_bom_generator.security import Redactor


class DependencyFileTests(unittest.TestCase):
    def test_detect_dependency_format_uses_declared_type_before_filename(self) -> None:
        self.assertEqual(detect_dependency_format("custom.lock", "pip"), "requirements")
        self.assertEqual(detect_dependency_format("custom.lock", "uv"), "uv")
        self.assertEqual(detect_dependency_format("uv.lock", None), "uv")
        self.assertEqual(detect_dependency_format("requirements-dev.txt", None), "requirements")
        self.assertIsNone(detect_dependency_format("poetry.lock", None))

    def test_requirements_parser_handles_pep508_hashes_and_skips_directives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "requirements.txt"
            path.write_text(
                "example-pinned==1.2.3 \\\n"
                "  --hash=sha256:abc123\n"
                'example-range[fast]>=2.0; python_version >= "3.12"\n'
                "example-wheel @ https://user:password@example.invalid/wheel.whl?token=secret-value\n"
                "-r nested.txt\n"
                "local-wheel @ file:///private/build/local-wheel.whl\n",
                encoding="utf-8",
                newline="\n",
            )

            result = parse_dependency_file(path, "requirements.txt", "requirements", Redactor("strict"))

            self.assertEqual([package.name for package in result.packages], [
                "example-pinned",
                "example-range",
                "example-wheel",
            ])
            pinned = next(package for package in result.packages if package.name == "example-pinned")
            ranged = next(package for package in result.packages if package.name == "example-range")
            wheel = next(package for package in result.packages if package.name == "example-wheel")
            self.assertEqual(pinned.version, "1.2.3")
            self.assertEqual(ranged.extras, ("fast",))
            self.assertIn("python_version", ranged.marker or "")
            self.assertEqual(wheel.source_type, "url")
            self.assertEqual(
                wheel.source_locator,
                "https://REDACTEDexample.invalid/wheel.whl?token=REDACTED",
            )
            self.assertNotIn("password", wheel.requirement)
            self.assertNotIn("secret-value", wheel.requirement)
            self.assertEqual(result.skipped_entries, 2)
            self.assertEqual(result.first_issue.location if result.first_issue else None, "line:5")

    def test_uv_lock_parser_collects_registry_and_editable_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "uv.lock"
            path.write_text(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "example-locked"\n'
                'version = "4.5.6"\n'
                'source = { registry = "https://pypi.org/simple" }\n\n'
                "[[package]]\n"
                'name = "workspace-model"\n'
                'source = { editable = "." }\n',
                encoding="utf-8",
                newline="\n",
            )

            result = parse_dependency_file(path, "uv.lock", "uv", Redactor("strict"))

            self.assertEqual(len(result.packages), 2)
            locked = next(package for package in result.packages if package.name == "example-locked")
            workspace = next(package for package in result.packages if package.name == "workspace-model")
            self.assertEqual(locked.version, "4.5.6")
            self.assertEqual(locked.source_type, "registry")
            self.assertEqual(locked.source_locator, "https://pypi.org/simple")
            self.assertIsNone(workspace.version)
            self.assertEqual(workspace.source_type, "editable")
            self.assertEqual(workspace.source_locator, ".")

    def test_uv_lock_keeps_same_package_from_distinct_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "uv.lock"
            path.write_text(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "same-package"\n'
                'version = "1.0.0"\n'
                'source = { git = "https://example.invalid/a.git?rev=111" }\n\n'
                "[[package]]\n"
                'name = "same-package"\n'
                'version = "1.0.0"\n'
                'source = { git = "https://example.invalid/b.git?rev=222" }\n',
                encoding="utf-8",
                newline="\n",
            )

            result = parse_dependency_file(path, "uv.lock", "uv", Redactor("strict"))

            self.assertEqual(len(result.packages), 2)
            self.assertEqual(
                {package.source_locator for package in result.packages},
                {
                    "https://example.invalid/a.git?rev=111",
                    "https://example.invalid/b.git?rev=222",
                },
            )
            self.assertEqual(len({package.identity_key() for package in result.packages}), 2)

    def test_dependency_file_read_limit_fails_without_partial_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "requirements.txt"
            path.write_text("example==1.0.0\n", encoding="utf-8", newline="\n")

            with patch.object(dependency_files, "MAX_DEPENDENCY_FILE_BYTES", 4):
                with self.assertRaises(DependencyFileLimitError):
                    parse_dependency_file(path, "requirements.txt", "requirements", Redactor("strict"))


if __name__ == "__main__":
    unittest.main()
