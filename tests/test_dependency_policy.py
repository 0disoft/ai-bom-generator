import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DependencyPolicyTests(unittest.TestCase):
    def test_tool_updates_have_one_owner_and_exact_annotation_matches(self):
        config = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
        self.assertEqual(config["enabledManagers"], ["custom.regex"])
        self.assertFalse(config["automerge"])
        manager = config["customManagers"][0]
        pattern = re.sub(r"\(\?<([a-zA-Z]+)>", r"(?P<\1>", manager["matchStrings"][0])
        found = []
        for path in [ROOT / "action.yml", *sorted((ROOT / ".github/workflows").glob("*.yml"))]:
            found.extend((path.name, match.group("depName"), match.group("currentValue"))
                         for match in re.finditer(pattern, path.read_text(encoding="utf-8")))
        self.assertEqual(sorted((name, dep) for name, dep, _ in found), [
            ("action.yml", "astral-sh/uv"), ("ci.yml", "astral-sh/uv"),
            ("ci.yml", "bun"), ("publish-pypi.yml", "astral-sh/uv"),
        ])
        self.assertTrue(all(re.fullmatch(r"\d+\.\d+\.\d+", version) for _, _, version in found))
        self.assertEqual(config["packageRules"], [
            {"matchUpdateTypes": ["major"], "dependencyDashboardApproval": True},
        ])
