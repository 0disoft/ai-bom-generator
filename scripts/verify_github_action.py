from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "action.yml"
ENTRYPOINT = ROOT / "scripts" / "github_action_entrypoint.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the local GitHub Action wrapper.")
    parser.parse_args(argv)
    _verify_action_metadata()
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        cases = [
            ActionCase(
                "clean",
                "tests/fixtures/complete-project",
                "tests/fixtures/complete-project/aibom.toml",
                "allow",
                0,
                "success",
                "complete",
            ),
            ActionCase(
                "default-paths",
                "tests/fixtures/complete-project",
                "tests/fixtures/complete-project/aibom.toml",
                "allow",
                0,
                "success",
                "complete",
                explicit_output_paths=False,
            ),
            ActionCase(
                "warning",
                "tests/fixtures/sparse-project",
                "tests/fixtures/sparse-project/aibom.toml",
                "allow",
                0,
                "success-with-warnings",
                "partial",
            ),
            ActionCase(
                "fail-on-warning",
                "tests/fixtures/sparse-project",
                "tests/fixtures/sparse-project/aibom.toml",
                "fail",
                10,
                "failed",
                "partial",
            ),
        ]
        for case in cases:
            _run_case(case, work / case.name)
        _run_missing_required_input_case(work / "missing-model-directory")
    return 0


class ActionCase:
    def __init__(
        self,
        name: str,
        model_directory: str,
        config: str,
        warnings: str,
        expected_exit: int,
        expected_status: str,
        expected_completeness_status: str,
        explicit_output_paths: bool = True,
    ) -> None:
        self.name = name
        self.model_directory = model_directory
        self.config = config
        self.warnings = warnings
        self.expected_exit = expected_exit
        self.expected_status = expected_status
        self.expected_completeness_status = expected_completeness_status
        self.explicit_output_paths = explicit_output_paths


def _verify_action_metadata() -> None:
    text = ACTION.read_text(encoding="utf-8")
    required_snippets = [
        "using: composite",
        "INPUT_MODEL_DIRECTORY",
        "scripts/github_action_entrypoint.py",
        "steps.generate.outputs['bom-path']",
        "steps.generate.outputs['warning-count']",
        "steps.generate.outputs.status",
        "steps.generate.outputs['completeness-status']",
        "steps.generate.outputs['exit-code']",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in text]
    if missing:
        raise AssertionError(f"action.yml is missing required snippets: {', '.join(missing)}")


def _run_case(case: ActionCase, case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    runner_temp = case_root / "runner-temp"
    if case.explicit_output_paths:
        output = case_root / "bom.cdx.json"
        warning_report = case_root / "warnings.json"
        summary = case_root / "summary.json"
    else:
        default_output_root = runner_temp / "ai-bom-generator"
        output = default_output_root / "bom.cdx.json"
        warning_report = default_output_root / "warnings.json"
        summary = default_output_root / "summary.json"
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(runner_temp),
            "INPUT_MODEL_DIRECTORY": case.model_directory,
            "INPUT_CONFIG": case.config,
            "INPUT_FORMAT": "cyclonedx-json-1.7",
            "INPUT_OUTPUT": str(output) if case.explicit_output_paths else "",
            "INPUT_WARNING_REPORT": str(warning_report) if case.explicit_output_paths else "",
            "INPUT_SUMMARY": str(summary) if case.explicit_output_paths else "",
            "INPUT_WARNINGS": case.warnings,
            "INPUT_REDACTION": "strict",
        }
    )
    result = subprocess.run(
        [sys.executable, str(ENTRYPOINT)],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != case.expected_exit:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"{case.name} returned {result.returncode}, expected {case.expected_exit}")
    for path in (output, warning_report, summary, github_output):
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"{case.name} did not create non-empty file: {path}")
    outputs = _read_github_output(github_output)
    if outputs.get("exit-code") != str(case.expected_exit):
        raise AssertionError(f"{case.name} output exit-code mismatch: {outputs.get('exit-code')}")
    if outputs.get("status") != case.expected_status:
        raise AssertionError(f"{case.name} output status mismatch: {outputs.get('status')}")
    if outputs.get("completeness-status") != case.expected_completeness_status:
        raise AssertionError(f"{case.name} output completeness-status mismatch: {outputs.get('completeness-status')}")
    if outputs.get("format") != "cyclonedx-json-1.7":
        raise AssertionError(f"{case.name} output format mismatch: {outputs.get('format')}")
    if outputs.get("bom-path") != output.as_posix():
        raise AssertionError(f"{case.name} output bom-path mismatch: {outputs.get('bom-path')}")
    if outputs.get("warning-report-path") != warning_report.as_posix():
        raise AssertionError(f"{case.name} output warning-report-path mismatch: {outputs.get('warning-report-path')}")
    if outputs.get("summary-path") != summary.as_posix():
        raise AssertionError(f"{case.name} output summary-path mismatch: {outputs.get('summary-path')}")


def _run_missing_required_input_case(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(case_root / "runner-temp"),
            "INPUT_MODEL_DIRECTORY": "",
            "INPUT_CONFIG": "",
            "INPUT_FORMAT": "cyclonedx-json-1.7",
            "INPUT_OUTPUT": "",
            "INPUT_WARNING_REPORT": "",
            "INPUT_SUMMARY": "",
            "INPUT_WARNINGS": "allow",
            "INPUT_REDACTION": "strict",
        }
    )
    result = subprocess.run(
        [sys.executable, str(ENTRYPOINT)],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 20:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"missing-model-directory returned {result.returncode}, expected 20")
    outputs = _read_github_output(github_output)
    if outputs.get("exit-code") != "20":
        raise AssertionError(f"missing-model-directory output exit-code mismatch: {outputs.get('exit-code')}")


def _read_github_output(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key:
            pairs[key] = value
    return pairs


if __name__ == "__main__":
    raise SystemExit(main())
