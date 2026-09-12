from pathlib import Path
import re
import tomllib
import unittest

import yaml

from ai_bom_generator import __version__
from ai_bom_generator.app import _SUPPORTED_EXPORT_FORMATS


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_action_documentation_matches_all_metadata_inputs_and_outputs(self):
        action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
        doc = (ROOT / "docs/github-action/inputs-and-outputs.md").read_text(encoding="utf-8")
        inputs = doc.split("## Inputs\n", 1)[1].split("## Outputs\n", 1)[0]
        outputs = doc.split("## Outputs\n", 1)[1].split("## Review Blockers\n", 1)[0]
        for key, section in [("inputs", inputs), ("outputs", outputs)]:
            self.assertEqual(set(re.findall(r"^- `([^`]+)`", section, re.MULTILINE)), set(action[key]))
        self.assertEqual(action["branding"], {"icon": "package", "color": "blue"})

    def test_current_formats_and_package_versions_do_not_drift(self):
        for path in ["README.md", "docs/cli/command-contract.md", "docs/github-action/inputs-and-outputs.md"]:
            doc = (ROOT / path).read_text(encoding="utf-8")
            for value in _SUPPORTED_EXPORT_FORMATS:
                self.assertIn(value, doc, path)
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
        package = next(p for p in lock["package"] if p["name"] == project["name"])
        self.assertEqual(project["version"], package["version"])
        self.assertEqual(project["version"], __version__)
