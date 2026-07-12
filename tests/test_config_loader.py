from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ai_bom_generator.config.loader import MAX_CONFIG_BYTES, load_config
from ai_bom_generator.errors import InvalidInputError
from ai_bom_generator.security import PathPolicy


class ConfigLoaderTests(unittest.TestCase):
    def test_config_over_read_budget_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "aibom.toml"
            config.write_bytes(b"#" * (MAX_CONFIG_BYTES + 1))

            with self.assertRaisesRegex(InvalidInputError, "byte read limit"):
                load_config(config, PathPolicy(root))

    def test_combined_reference_budget_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "aibom.toml"
            entries = "".join(f'[[datasets]]\nname = "dataset-{index}"\n' for index in range(1001))
            config.write_text(f'schema_version = "1"\n{entries}', encoding="utf-8")

            with self.assertRaisesRegex(InvalidInputError, "1001 references; the limit is 1000"):
                load_config(config, PathPolicy(root))

    def test_artifact_pattern_budget_is_rejected_by_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "aibom.toml"
            patterns = ", ".join(f'"models/{index}.bin"' for index in range(257))
            config.write_text(
                f'schema_version = "1"\n[artifacts]\ninclude = [{patterns}]\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(InvalidInputError, "is too long"):
                load_config(config, PathPolicy(root))


if __name__ == "__main__":
    unittest.main()
