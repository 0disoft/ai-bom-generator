from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import tracemalloc
import unittest
from unittest.mock import patch

from ai_bom_generator.collectors import artifacts


class ArtifactCollectionTests(unittest.TestCase):
    def test_large_nonmatching_tree_has_bounded_scan_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for directory in range(16):
                parent = root / str(directory)
                parent.mkdir()
                for index in range(128):
                    (parent / f"{index}.txt").touch()
            spec = artifacts._ArtifactPatternSpec("**/*.bin", "artifacts.include", (), False)
            tracemalloc.start()
            start = time.perf_counter()
            try:
                result = artifacts._scan_candidate_artifact_paths(root, [spec])
                elapsed = time.perf_counter() - start
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertEqual(result[0].matches, [])
            print(f"Artifact scan: 2064 entries, {elapsed:.3f}s, {peak} traced bytes")

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
            real_scandir = os.scandir

            def recording_scan(path):
                visited.append(Path(path).relative_to(root).as_posix())
                return real_scandir(path)

            spec = artifacts._ArtifactPatternSpec(
                pattern="**/*.safetensors",
                source_field="artifacts.discovery",
                excludes=artifacts._DISCOVERED_ARTIFACT_EXCLUDES,
                discovery=True,
            )
            with patch.object(artifacts.os, "scandir", side_effect=recording_scan):
                results = artifacts._scan_candidate_artifact_paths(root, [spec])

            self.assertEqual(len(visited), len(set(visited)))
            self.assertIn("models", visited)
            self.assertNotIn("node_modules", visited)
            self.assertEqual(
                [path.relative_to(root).as_posix() for path in results[0].matches],
                ["models/model.safetensors"],
            )

    def test_traversal_budget_counts_nonmatching_entries_and_accepts_exact_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in range(20):
                (root / f"{index}.txt").touch()
            spec = artifacts._ArtifactPatternSpec("**/*.bin", "artifacts.include", (), False)
            with patch.object(artifacts, "_MAX_VISITED_ENTRIES", 20):
                self.assertEqual(artifacts._scan_candidate_artifact_paths(root, [spec])[0].matches, [])
                (root / "model.bin").touch()
                with self.assertRaises(artifacts.ArtifactTraversalLimit):
                    artifacts._scan_candidate_artifact_paths(root, [spec])

    def test_traversal_overflow_discards_all_partial_artifact_matches(self):
        from ai_bom_generator.config import LoadedConfig
        from ai_bom_generator.security import PathPolicy

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "first.bin").touch()
            (root / "other.txt").touch()
            warnings = []
            with patch.object(artifacts, "_MAX_VISITED_ENTRIES", 1):
                selected = artifacts.collect_artifacts(
                    LoadedConfig(None, {"artifacts": {"include": ["*.bin"]}}),
                    PathPolicy(root), warnings,
                )
            self.assertEqual(selected, [])
            self.assertEqual([w.code for w in warnings], ["ARTIFACT_TRAVERSAL_LIMIT_EXCEEDED"])


if __name__ == "__main__":
    unittest.main()
