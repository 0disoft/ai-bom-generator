from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import tempfile
import time
import tracemalloc

from ai_bom_generator.cli import main
from ai_bom_generator.errors import ExitCode


BENCHMARK_SCHEMA_VERSION = "ai-bom-performance/v1"
DEFAULT_SIZES = (100, 500, 1000)
REPEATS = 3
MEMORY_REPEATS = 1
BUDGETS = {
    100: {"median_seconds": 2.0, "peak_bytes": 16 * 1024 * 1024},
    500: {"median_seconds": 4.0, "peak_bytes": 32 * 1024 * 1024},
    1000: {"median_seconds": 8.0, "peak_bytes": 64 * 1024 * 1024},
}


def main_entry(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure bounded AI-BOM component generation costs.")
    parser.add_argument("--check", action="store_true", help="Fail when a documented budget is exceeded.")
    parser.add_argument("--json", action="store_true", help="Write the complete benchmark result as JSON.")
    args = parser.parse_args(argv)

    result = run_benchmarks(DEFAULT_SIZES)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_summary(result)
    return 1 if args.check and result["status"] != "passed" else 0


def run_benchmarks(sizes: tuple[int, ...]) -> dict[str, object]:
    cases = [_run_case(size) for size in sizes]
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "measurement": {
            "time": "median wall-clock seconds across three uninstrumented in-process runs",
            "memory": "Python traced allocation peak from one separate in-process run",
        },
        "status": "passed" if all(case["status"] == "passed" for case in cases) else "failed",
        "cases": cases,
    }


def _run_case(component_count: int) -> dict[str, object]:
    budget = BUDGETS.get(component_count)
    if budget is None:
        raise ValueError(f"No performance budget is defined for {component_count} components.")

    durations: list[float] = []
    for repeat in range(REPEATS):
        gc.collect()
        started = time.perf_counter()
        _generate(component_count, repeat)
        durations.append(time.perf_counter() - started)

    gc.collect()
    tracemalloc.start()
    try:
        _generate(component_count, REPEATS)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    median_seconds = statistics.median(durations)
    passed = median_seconds <= budget["median_seconds"] and peak_bytes <= budget["peak_bytes"]
    return {
        "component_count": component_count,
        "time_repeats": REPEATS,
        "memory_repeats": MEMORY_REPEATS,
        "median_seconds": round(median_seconds, 6),
        "peak_bytes": peak_bytes,
        "budget": budget,
        "status": "passed" if passed else "failed",
    }


def _generate(component_count: int, repeat: int) -> None:
    with tempfile.TemporaryDirectory(prefix=f"ai-bom-perf-{component_count}-{repeat}-") as temp:
        work = Path(temp)
        project = work / "project"
        project.mkdir()
        config = project / "aibom.toml"
        config.write_text(_config_text(component_count), encoding="utf-8", newline="\n")
        output = work / "bom.json"
        summary = work / "summary.json"

        code = main(
            [
                "generate",
                str(project),
                "--config",
                str(config),
                "--output",
                str(output),
                "--warning-report",
                str(work / "warnings.json"),
                "--summary",
                str(summary),
            ]
        )
        if code != ExitCode.SUCCESS:
            raise RuntimeError(f"benchmark generation failed for {component_count} components with exit code {code}")
        payload = json.loads(output.read_text(encoding="utf-8"))
        components = payload.get("components")
        if not isinstance(components, list) or len(components) != component_count:
            raise RuntimeError(
                f"benchmark generated {len(components) if isinstance(components, list) else 'invalid'} "
                f"components, expected {component_count}"
            )


def _config_text(component_count: int) -> str:
    lines = [
        'schema_version = "1"',
        "",
        "[model]",
        'name = "performance-fixture"',
        'version = "1.0.0"',
        'license_declared = "NOASSERTION"',
    ]
    for index in range(component_count):
        lines.extend(
            [
                "",
                "[[datasets]]",
                f'name = "dataset-{index:04d}"',
                'license_declared = "NOASSERTION"',
            ]
        )
    return "\n".join(lines) + "\n"


def _print_summary(result: dict[str, object]) -> None:
    print(f"component performance: {result['status']}")
    cases = result["cases"]
    if not isinstance(cases, list):
        return
    for case in cases:
        if not isinstance(case, dict):
            continue
        print(
            f"{case['component_count']}: median={case['median_seconds']}s "
            f"peak={case['peak_bytes']} bytes status={case['status']}"
        )


if __name__ == "__main__":
    raise SystemExit(main_entry())
