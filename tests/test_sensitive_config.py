from pathlib import Path
import unittest

from ai_bom_generator.config import LoadedConfig
from ai_bom_generator.config.sensitive_keys import sensitive_config_warnings


class SensitiveConfigTests(unittest.TestCase):
    def test_nested_keys_warn_without_copying_caller_keys_values_or_paths(self):
        config = LoadedConfig(Path("private-name.toml"), {
            "model": {"private-container": {"api_key": "synthetic-value"}},
            "datasets": [{"password": "synthetic-value"}],
        })
        warnings = sensitive_config_warnings(config)
        self.assertEqual([item.object_id for item in warnings], ["model", "datasets[0]"])
        rendered = str([item.to_json() for item in warnings])
        for text in ("private-container", "api_key", "synthetic-value", "private-name"):
            self.assertNotIn(text, rendered)

    def test_benign_names_do_not_warn(self):
        self.assertEqual(sensitive_config_warnings(LoadedConfig(None, {
            "model": {"tokenizer": "bpe", "secret_count": 0, "monkey": "value"},
        })), [])

    def test_warning_does_not_depend_on_redaction_mode_or_provider_shape(self):
        result = sensitive_config_warnings(LoadedConfig(None, {"model": {"token": 0}}))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, "SENSITIVE_CONFIG_KEY")
