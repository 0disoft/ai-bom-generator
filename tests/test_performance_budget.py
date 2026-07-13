from __future__ import annotations

from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from benchmark_components import BENCHMARK_SCHEMA_VERSION, run_benchmarks  # noqa: E402


class PerformanceBudgetTests(unittest.TestCase):
    def test_small_benchmark_emits_versioned_result(self) -> None:
        result = run_benchmarks((100,))

        self.assertEqual(result["schema_version"], BENCHMARK_SCHEMA_VERSION)
        self.assertEqual(result["status"], "passed")
        cases = result["cases"]
        self.assertIsInstance(cases, list)
        self.assertEqual(cases[0]["component_count"], 100)
        self.assertEqual(cases[0]["time_repeats"], 3)
        self.assertEqual(cases[0]["memory_repeats"], 1)
        self.assertEqual(cases[0]["status"], "passed")
