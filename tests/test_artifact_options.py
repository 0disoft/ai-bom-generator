from pathlib import Path
import tempfile
import unittest

from ai_bom_generator.cli import build_parser
from ai_bom_generator.config import LoadedConfig, load_config
from ai_bom_generator.config.artifact_options import LIMIT_CEILINGS, apply_artifact_overrides
from ai_bom_generator.collectors.artifacts import collect_artifacts
from ai_bom_generator.errors import InvalidInputError
from ai_bom_generator.security import PathPolicy


class ArtifactOptionTests(unittest.TestCase):
    def test_overrides_preserve_defaults_and_do_not_mutate_config(self):
        original = LoadedConfig(None, {"artifacts": {"discovery": True, "limits": {"visited_entries": 100}}})
        unchanged = apply_artifact_overrides(original, None, {})
        self.assertEqual(unchanged.data, original.data)
        result = apply_artifact_overrides(original, False, {"visited_entries": 20})
        self.assertFalse(result.data["artifacts"]["discovery"])
        self.assertEqual(result.data["artifacts"]["limits"]["visited_entries"], 20)
        self.assertEqual(original.data["artifacts"]["limits"]["visited_entries"], 100)

    def test_all_limits_reject_invalid_and_above_ceiling_values(self):
        for key, ceiling in LIMIT_CEILINGS.items():
            for value in (0, -1, True, 1.5, ceiling + 1):
                with self.subTest(key=key, value=value), self.assertRaises(InvalidInputError):
                    apply_artifact_overrides(LoadedConfig(None, {}), None, {key: value})
            apply_artifact_overrides(LoadedConfig(None, {}), None, {key: ceiling})

    def test_cli_boolean_override_supports_explicit_disable(self):
        base = ["generate", ".", "--output", "a", "--warning-report", "b"]
        parser = build_parser()
        self.assertIsNone(parser.parse_args(base).discover_artifacts)
        self.assertTrue(parser.parse_args(base + ["--discover-artifacts"]).discover_artifacts)
        self.assertFalse(parser.parse_args(base + ["--no-discover-artifacts"]).discover_artifacts)

    def test_config_limits_reach_collection_and_schema_rejects_overrides(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.bin").write_bytes(b"data")
            (root / "b.bin").write_bytes(b"data")
            config_path = root / "aibom.toml"
            config_path.write_text('schema_version="1"\n[artifacts]\ninclude=["*.bin"]\n[artifacts.limits]\nmatches_per_pattern=1\n')
            policy = PathPolicy(root)
            config = load_config(None, policy)
            warnings = []
            self.assertEqual(collect_artifacts(config, policy, warnings), [])
            self.assertEqual(warnings[0].code, "ARTIFACT_MATCH_LIMIT_EXCEEDED")
            raised = apply_artifact_overrides(config, None, {"matches_per_pattern": 2, "single_file_bytes": 3})
            warnings = []
            self.assertEqual(collect_artifacts(raised, policy, warnings), [])
            self.assertEqual([w.code for w in warnings], ["ARTIFACT_SIZE_LIMIT_EXCEEDED"] * 2)
            config_path.write_text('schema_version="1"\n[artifacts.limits]\nvisited_entries=100001\n')
            with self.assertRaises(InvalidInputError):
                load_config(None, policy)
