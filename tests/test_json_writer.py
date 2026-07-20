from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.reporting import json_writer
from ai_bom_generator.reporting.json_writer import (
    OutputSetLockedError,
    write_json_output_set,
)


class JsonWriterTests(unittest.TestCase):
    def test_output_set_lock_rejects_overlapping_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            output = work / "bom.json"
            manifest = work / "manifest.json"

            with json_writer._output_set_lock([output, manifest]):
                with self.assertRaises(OutputSetLockedError):
                    write_json_output_set([("bom", output, {"run": "B"})], manifest)

            self.assertFalse(output.exists())
            self.assertFalse(manifest.exists())

    def test_shared_output_path_is_locked_across_different_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            output = work / "bom.json"
            first_manifest = work / "manifest-a.json"
            second_manifest = work / "manifest-b.json"

            with json_writer._output_set_lock([output, first_manifest]):
                with self.assertRaisesRegex(OutputSetLockedError, "bom.json"):
                    write_json_output_set([("bom", output, {"run": "B"})], second_manifest)

            self.assertFalse(output.exists())
            self.assertFalse(first_manifest.exists())
            self.assertFalse(second_manifest.exists())

    def test_replace_failure_restores_previous_committed_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            output = work / "bom.json"
            warning_report = work / "warnings.json"
            manifest = work / "manifest.json"
            write_json_output_set(
                [
                    ("bom", output, {"run": "old"}),
                    ("warning_report", warning_report, {"run": "old"}),
                ],
                manifest,
            )
            old_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            real_replace = json_writer.os.replace
            failed = False

            def fail_new_warning_once(source: Path | str, destination: Path | str) -> None:
                nonlocal failed
                destination_path = Path(destination)
                source_path = Path(source)
                if not failed and destination_path == warning_report and source_path.name.startswith(".warnings.json."):
                    failed = True
                    raise OSError("blocked replacement")
                real_replace(source, destination)

            with patch.object(json_writer.os, "replace", side_effect=fail_new_warning_once):
                with self.assertRaisesRegex(OSError, "blocked replacement"):
                    write_json_output_set(
                        [
                            ("bom", output, {"run": "new"}),
                            ("warning_report", warning_report, {"run": "new"}),
                        ],
                        manifest,
                    )

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"run": "old"})
            self.assertEqual(json.loads(warning_report.read_text(encoding="utf-8")), {"run": "old"})
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), old_manifest)
            self.assertEqual([], list(work.glob(".*.tmp")))


if __name__ == "__main__":
    unittest.main()
