from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
import shutil
import tempfile
import unittest

from ai_bom_generator.cli import main
from ai_bom_generator.errors import ExitCode
from ai_bom_generator.validation import validate_with_schema


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMAS = ROOT / "schemas"


class ContractSchemaTests(unittest.TestCase):
    def test_fixture_configs_validate_against_config_schema(self) -> None:
        schema = SCHEMAS / "aibom-config-v1.schema.json"
        for config in sorted(FIXTURES.glob("*/aibom.toml")):
            if config.parent.name == "invalid-config":
                continue
            with self.subTest(config=config.parent.name):
                import tomllib

                payload = tomllib.loads(config.read_text(encoding="utf-8"))
                validate_with_schema(payload, schema, "AI-BOM config v1")

    def test_packaged_config_schema_matches_contract_schema(self) -> None:
        packaged = resources.files("ai_bom_generator.config.schema").joinpath("aibom-config-v1.schema.json")
        with resources.as_file(packaged) as packaged_path:
            self.assertEqual(
                json.loads(packaged_path.read_text(encoding="utf-8")),
                json.loads((SCHEMAS / "aibom-config-v1.schema.json").read_text(encoding="utf-8")),
            )

    def test_generated_summary_warning_report_and_manifest_validate_against_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(FIXTURES / "sparse-project", project)
            summary = work / "summary.json"
            warnings = work / "warnings.json"
            manifest = work / "manifest.json"

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
                    "--manifest",
                    str(manifest),
                ]
            )

            self.assertEqual(code, ExitCode.SUCCESS)
            validate_with_schema(_read_json(summary), SCHEMAS / "aibom-summary-v1.schema.json", "AI-BOM summary v1")
            validate_with_schema(
                _read_json(warnings),
                SCHEMAS / "aibom-warning-report-v1.schema.json",
                "AI-BOM warning report v1",
            )
            validate_with_schema(
                _read_json(manifest),
                SCHEMAS / "aibom-output-manifest-v1.schema.json",
                "AI-BOM output manifest v1",
            )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
