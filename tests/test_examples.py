from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_bom_generator.cli import main
from ai_bom_generator.errors import ExitCode


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class ExampleTests(unittest.TestCase):
    def test_minimal_model_project_quickstart_generates_outputs(self) -> None:
        project = EXAMPLES / "minimal-model-project"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            bom = output / "bom.cdx.json"
            warnings = output / "warnings.json"
            summary = output / "summary.json"

            code = main(
                [
                    "generate",
                    str(project),
                    "--format",
                    "cyclonedx-json-1.7",
                    "--output",
                    str(bom),
                    "--warning-report",
                    str(warnings),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            self.assertTrue(bom.is_file())
            self.assertTrue(warnings.is_file())
            self.assertTrue(summary.is_file())
