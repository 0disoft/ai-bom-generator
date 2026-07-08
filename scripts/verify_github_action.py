from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import github_action_entrypoint


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
                "config-warning-policy",
                "tests/fixtures/sparse-project",
                None,
                None,
                10,
                "failed",
                "partial",
                config_text=(
                    'schema_version = "1"\n\n'
                    '[model]\nname = "sparse-model"\n\n'
                    '[warning_policy]\nmissing_metadata = "fail"\n'
                ),
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
        _run_stale_summary_failure_case(work / "stale-summary-failure")
        _verify_github_output_escaping(work / "escaped-github-output")
    return 0


class ActionCase:
    def __init__(
        self,
        name: str,
        model_directory: str,
        config: str | None,
        warnings: str | None,
        expected_exit: int,
        expected_status: str,
        expected_completeness_status: str,
        explicit_output_paths: bool = True,
        format: str | None = "cyclonedx-json-1.7",
        config_text: str | None = None,
    ) -> None:
        self.name = name
        self.model_directory = model_directory
        self.config = config
        self.warnings = warnings
        self.expected_exit = expected_exit
        self.expected_status = expected_status
        self.expected_completeness_status = expected_completeness_status
        self.explicit_output_paths = explicit_output_paths
        self.format = format
        self.config_text = config_text


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
        output = None
        warning_report = None
        summary = None
    model_directory = case.model_directory
    config = case.config
    if case.config_text is not None:
        project = case_root / "project"
        shutil.copytree(ROOT / case.model_directory, project)
        model_directory = str(project)
        config_path = project / "aibom.toml"
        config_path.write_text(case.config_text, encoding="utf-8", newline="\n")
        config = str(config_path)
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(runner_temp),
            "INPUT_MODEL_DIRECTORY": model_directory,
            "INPUT_CONFIG": config or "",
            "INPUT_FORMAT": case.format or "",
            "INPUT_OUTPUT": str(output) if output else "",
            "INPUT_WARNING_REPORT": str(warning_report) if warning_report else "",
            "INPUT_SUMMARY": str(summary) if summary else "",
            "INPUT_WARNINGS": case.warnings or "",
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
    if not github_output.is_file() or github_output.stat().st_size == 0:
        raise AssertionError(f"{case.name} did not create non-empty file: {github_output}")
    outputs = _read_github_output(github_output)
    if output is None:
        output = Path(outputs.get("bom-path", ""))
        warning_report = Path(outputs.get("warning-report-path", ""))
        summary = Path(outputs.get("summary-path", ""))
    for path in (output, warning_report, summary, github_output):
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"{case.name} did not create non-empty file: {path}")
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
    if not case.explicit_output_paths and output.parent == runner_temp / "ai-bom-generator":
        raise AssertionError(f"{case.name} default output path did not include a run-unique directory")

    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    if str(summary_payload.get("status")) != case.expected_status:
        raise AssertionError(f"{case.name} summary status mismatch: {summary_payload.get('status')}")


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


def _run_stale_summary_failure_case(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    output = case_root / "bom.cdx.json"
    warning_report = case_root / "warnings.json"
    summary = case_root / "summary.json"
    for path in (output, warning_report, summary):
        path.write_text('{"status":"stale","warning_count":999}\n', encoding="utf-8", newline="\n")
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(case_root / "runner-temp"),
            "INPUT_MODEL_DIRECTORY": "tests/fixtures/complete-project",
            "INPUT_CONFIG": "tests/fixtures/complete-project/aibom.toml",
            "INPUT_FORMAT": "spdx-ai",
            "INPUT_OUTPUT": str(output),
            "INPUT_WARNING_REPORT": str(warning_report),
            "INPUT_SUMMARY": str(summary),
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
    if result.returncode != 40:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"stale-summary-failure returned {result.returncode}, expected 40")
    outputs = _read_github_output(github_output)
    if outputs.get("exit-code") != "40":
        raise AssertionError(f"stale-summary-failure output exit-code mismatch: {outputs.get('exit-code')}")
    for key in ("warning-count", "status", "completeness-status", "format"):
        if key in outputs:
            raise AssertionError(f"stale-summary-failure published stale summary output key: {key}")
    for path in (output, warning_report, summary):
        if path.exists():
            raise AssertionError(f"stale-summary-failure left stale file: {path}")


def _verify_github_output_escaping(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    previous = os.environ.get("GITHUB_OUTPUT")
    os.environ["GITHUB_OUTPUT"] = str(github_output)
    try:
        github_action_entrypoint._append_github_outputs(
            {
                "bom-path": "safe-path\nforged-output=bad",
                "status": "success",
            }
        )
    finally:
        if previous is None:
            os.environ.pop("GITHUB_OUTPUT", None)
        else:
            os.environ["GITHUB_OUTPUT"] = previous
    outputs = _read_github_output(github_output)
    if outputs.get("bom-path") != "safe-path\nforged-output=bad":
        raise AssertionError(f"escaped output value mismatch: {outputs.get('bom-path')}")
    if outputs.get("status") != "success":
        raise AssertionError(f"escaped status mismatch: {outputs.get('status')}")
    if "forged-output" in outputs:
        raise AssertionError("newline output value created a forged GitHub output key")


def _read_github_output(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if "<<" in line:
            key, _, delimiter = line.partition("<<")
            if not key or not delimiter:
                raise AssertionError(f"Malformed GitHub output line: {line}")
            index += 1
            value_lines: list[str] = []
            while index < len(lines) and lines[index] != delimiter:
                value_lines.append(lines[index])
                index += 1
            if index >= len(lines):
                raise AssertionError(f"Missing GitHub output delimiter for {key}: {delimiter}")
            pairs[key] = "\n".join(value_lines)
            index += 1
            continue
        key, _, value = line.partition("=")
        if key:
            pairs[key] = value
        index += 1
    return pairs


if __name__ == "__main__":
    raise SystemExit(main())
