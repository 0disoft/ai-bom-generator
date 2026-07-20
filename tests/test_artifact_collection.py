from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.collectors import artifacts


class ArtifactCollectionTests(unittest.TestCase):
    def test_non_recursive_glob_does_not_cross_directory_boundaries(self) -> None:
        self.assertTrue(artifacts._matches_glob("model.bin", "*.bin"))
        self.assertFalse(artifacts._matches_glob("models/model.bin", "*.bin"))
        self.assertTrue(artifacts._matches_glob("models/model.bin", "**/*.bin"))

    def test_discovery_prunes_excluded_subtrees_during_single_walk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "models").mkdir()
            (root / "models" / "model.safetensors").write_bytes(b"model")
            (root / "node_modules" / "package").mkdir(parents=True)
            (root / "node_modules" / "package" / "hidden.safetensors").write_bytes(b"hidden")
            visited: list[str] = []
            real_walk = os.walk

            def recording_walk(*args: object, **kwargs: object):
                for current_root, directory_names, file_names in real_walk(*args, **kwargs):
                    visited.append(Path(current_root).relative_to(root).as_posix())
                    yield current_root, directory_names, file_names

            spec = artifacts._ArtifactPatternSpec(
                pattern="**/*.safetensors",
                source_field="artifacts.discovery",
                excludes=artifacts._DISCOVERED_ARTIFACT_EXCLUDES,
                discovery=True,
            )
            with patch.object(artifacts.os, "walk", side_effect=recording_walk) as walk:
                results = artifacts._scan_candidate_artifact_paths(root, [spec])

            self.assertEqual(walk.call_count, 1)
            self.assertIn("models", visited)
            self.assertNotIn("node_modules", visited)
            self.assertEqual(
                [path.relative_to(root).as_posix() for path in results[0].matches],
                ["models/model.safetensors"],
            )


if __name__ == "__main__":
    unittest.main()
