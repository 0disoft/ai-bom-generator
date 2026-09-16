from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import json
import tempfile
import unittest

from ai_bom_generator.cli import main
from ai_bom_generator.config.spdx_document import document_metadata
from ai_bom_generator.errors import InvalidInputError


class DocumentMetadataTests(unittest.TestCase):
    def test_explicit_metadata_and_override_normalize_utc(self):
        table = {"creator_name": " Example ", "creator_type": "Organization", "created": "2026-01-01T09:00:00+09:00"}
        self.assertEqual(document_metadata(table).created, "2026-01-01T00:00:00Z")
        self.assertEqual(document_metadata(table, "2026-02-01T00:00:00Z").created, "2026-02-01T00:00:00Z")
        self.assertEqual(document_metadata(table).creator_name, "Example")

    def test_no_inferred_authorship_or_clock(self):
        for table in ({}, {"creator_name": "Example"}, {"creator_name": " ", "creator_type": "Person"}):
            with self.assertRaises(InvalidInputError):
                document_metadata(table)
        for date in ("", "2026-01-01", "2026-02-30T00:00:00Z", "2026-01-01T00:00:00", "2026-01-01T00:00:00+00:99"):
            with self.subTest(date=date), self.assertRaises(InvalidInputError):
                document_metadata({"creator_name": "Example", "creator_type": "Person", "created": date})

    def test_cli_output_is_deterministic_and_missing_metadata_keeps_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            project = work / "project"
            project.mkdir()
            config = project / "aibom.toml"
            base = ('schema_version = "1"\n[model]\nname = "synthetic-model"\n'
                    'supplied_by = "Example Supplier"\ndownload_location = "https://example.invalid/model"\n')
            config.write_text(base, encoding="utf-8")
            output = work / "bom.json"
            output.write_text("previous", encoding="utf-8")
            args = ["generate", str(project), "--format", "spdx-json-3.0.1",
                    "--output", str(output), "--warning-report", str(work / "warnings.json")]
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertNotEqual(main(args), 0)
                self.assertEqual(output.read_text(), "previous")
                config.write_text(base + '[spdx]\ncreator_name = "Example"\ncreator_type = "Person"\n', encoding="utf-8")
                args += ["--document-created", "2026-01-01T00:00:00Z"]
                self.assertEqual(main(args), 0)
                first = output.read_bytes()
                self.assertEqual(main(args), 0)
                self.assertEqual(first, output.read_bytes())
            graph = json.loads(first)["@graph"]
            self.assertTrue(any(x["type"] == "Person" and x["name"] == "Example" for x in graph))
            model = next(x for x in graph if x["type"] == "ai_AIPackage")
            retained = json.loads(model["comment"])
            self.assertEqual(retained["suppliedBy"], "Example Supplier")
            self.assertEqual(retained["downloadLocation"], "https://example.invalid/model")
