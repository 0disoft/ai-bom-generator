from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import github_action_entrypoint


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "action.yml"
ENTRYPOINT = ROOT / "scripts" / "github_action_entrypoint.py"
WORKFLOWS = ROOT / ".github" / "workflows"
APPROVED_MOVING_ACTION_REFERENCES = {
    Path(".github/workflows/clarissimi.yml"): {"0disoft/clarissimi@v0"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the local GitHub Action wrapper.")
    parser.parse_args(argv)
    _verify_action_metadata()
    _verify_external_action_pins()
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
                "discovered-config",
                "tests/fixtures/complete-project",
                None,
                "allow",
                0,
                "success",
                "complete",
                format=None,
            ),
            ActionCase(
                "spdx-ai-format",
                "tests/fixtures/complete-project",
                "tests/fixtures/complete-project/aibom.toml",
                "allow",
                0,
                "success",
                "complete",
                format="spdx-ai",
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
        _run_relative_output_case(work / "relative-output-paths")
        _run_missing_required_input_case(work / "missing-model-directory")
        _run_stale_cleanup_failure_case(work / "stale-cleanup-failure")
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
        'version: "0.11.28"',
        'enable-cache: "false"',
        "working-directory: ${{ github.action_path }}",
        "INPUT_MODEL_DIRECTORY",
        "INPUT_MANIFEST",
        "INPUT_ERROR_REPORT",
        "scripts/github_action_entrypoint.py",
        "steps.generate.outputs['bom-path']",
        "steps.generate.outputs['manifest-path']",
        "steps.generate.outputs['error-report-path']",
        "steps.generate.outputs['error-code']",
        "steps.generate.outputs['error-stage']",
        "steps.generate.outputs['warning-count']",
        "steps.generate.outputs.status",
        "steps.generate.outputs['completeness-status']",
        "steps.generate.outputs['exit-code']",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in text]
    if missing:
        raise AssertionError(f"action.yml is missing required snippets: {', '.join(missing)}")

    _require_exact_action_pin(text, "actions/setup-python")
    _require_exact_action_pin(text, "astral-sh/setup-uv")

    entrypoint_text = ENTRYPOINT.read_text(encoding="utf-8")
    required_entrypoint_snippets = [
        '"--locked"',
        'env["UV_PROJECT_ENVIRONMENT"]',
        'env["UV_CACHE_DIR"]',
    ]
    missing_entrypoint = [snippet for snippet in required_entrypoint_snippets if snippet not in entrypoint_text]
    if missing_entrypoint:
        raise AssertionError(
            "GitHub Action entrypoint is missing runtime isolation snippets: "
            f"{', '.join(missing_entrypoint)}"
        )


def _require_exact_action_pin(text: str, action: str) -> str:
    uses_pattern = re.compile(
        rf"^\s*uses:\s*{re.escape(action)}@(?P<ref>[^\s#]+)\s+#\s+"
        rf"(?P<version>v[0-9]+\.[0-9]+\.[0-9]+)\s*$",
        re.MULTILINE,
    )
    matches = list(uses_pattern.finditer(text))
    if len(matches) != 1:
        raise AssertionError(
            f"action.yml must use {action} exactly once with a full commit SHA "
            f"and semver comment; found {len(matches)}"
        )

    ref = matches[0].group("ref")
    if re.fullmatch(r"[0-9a-f]{40}", ref) is None:
        raise AssertionError(f"action.yml must pin {action} to a full lowercase commit SHA; found {ref}")
    return ref


def _verify_external_action_pins() -> None:
    sources = [ACTION, *sorted(WORKFLOWS.glob("*.yml")), *sorted(WORKFLOWS.glob("*.yaml"))]
    invalid: list[str] = []
    pattern = re.compile(r"^\s*-?\s*uses:\s*(?P<target>[^\s#]+)(?:\s+#\s+(?P<comment>\S+))?\s*$")
    for source in sources:
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            match = pattern.match(line)
            if match is None:
                continue
            target = match.group("target")
            if target.startswith("./"):
                continue
            source_path = source.relative_to(ROOT)
            if target in APPROVED_MOVING_ACTION_REFERENCES.get(source_path, set()):
                continue
            action, separator, ref = target.rpartition("@")
            comment = match.group("comment") or ""
            if (
                not separator
                or re.fullmatch(r"[0-9a-f]{40}", ref) is None
                or re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", comment) is None
            ):
                invalid.append(f"{source.relative_to(ROOT)}:{line_number} ({action or target})")
    if invalid:
        raise AssertionError(
            "external GitHub Actions must use a full lowercase commit SHA and semver comment: "
            + ", ".join(invalid)
        )


def _run_case(case: ActionCase, case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    runner_temp = case_root / "runner-temp"
    if case.explicit_output_paths:
        output = case_root / "bom.cdx.json"
        warning_report = case_root / "warnings.json"
        summary = case_root / "summary.json"
        manifest = case_root / "output-manifest.json"
    else:
        output = None
        warning_report = None
        summary = None
        manifest = None
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
            "INPUT_MANIFEST": str(manifest) if manifest else "",
            "INPUT_ERROR_REPORT": "",
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
        manifest = Path(outputs.get("manifest-path", ""))
    assert manifest is not None
    for path in (output, warning_report, summary, manifest, github_output):
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"{case.name} did not create non-empty file: {path}")
    if outputs.get("exit-code") != str(case.expected_exit):
        raise AssertionError(f"{case.name} output exit-code mismatch: {outputs.get('exit-code')}")
    if outputs.get("status") != case.expected_status:
        raise AssertionError(f"{case.name} output status mismatch: {outputs.get('status')}")
    if outputs.get("completeness-status") != case.expected_completeness_status:
        raise AssertionError(f"{case.name} output completeness-status mismatch: {outputs.get('completeness-status')}")
    expected_format = case.format or "cyclonedx-json-1.7"
    if outputs.get("format") != expected_format:
        raise AssertionError(f"{case.name} output format mismatch: {outputs.get('format')}")
    if outputs.get("bom-path") != output.as_posix():
        raise AssertionError(f"{case.name} output bom-path mismatch: {outputs.get('bom-path')}")
    if outputs.get("warning-report-path") != warning_report.as_posix():
        raise AssertionError(f"{case.name} output warning-report-path mismatch: {outputs.get('warning-report-path')}")
    if outputs.get("summary-path") != summary.as_posix():
        raise AssertionError(f"{case.name} output summary-path mismatch: {outputs.get('summary-path')}")
    if outputs.get("manifest-path") != manifest.as_posix():
        raise AssertionError(f"{case.name} output manifest-path mismatch: {outputs.get('manifest-path')}")
    error_report = Path(outputs.get("error-report-path", ""))
    if not error_report.as_posix() or error_report.exists():
        raise AssertionError(f"{case.name} left an unexpected success-path error report: {error_report}")
    for key in ("error-code", "error-stage"):
        if key in outputs:
            raise AssertionError(f"{case.name} published failure output on success: {key}")
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
            "INPUT_MANIFEST": "",
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


def _run_relative_output_case(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    output = case_root / "bom.cdx.json"
    warning_report = case_root / "warnings.json"
    summary = case_root / "summary.json"
    manifest = case_root / "output-manifest.json"
    error_report = case_root / "error.json"

    def relative(path: Path) -> str:
        return os.path.relpath(path, ROOT)

    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(case_root / "runner-temp"),
            "INPUT_MODEL_DIRECTORY": "tests/fixtures/complete-project",
            "INPUT_CONFIG": "tests/fixtures/complete-project/aibom.toml",
            "INPUT_FORMAT": "cyclonedx-json-1.7",
            "INPUT_OUTPUT": relative(output),
            "INPUT_WARNING_REPORT": relative(warning_report),
            "INPUT_SUMMARY": relative(summary),
            "INPUT_MANIFEST": relative(manifest),
            "INPUT_ERROR_REPORT": relative(error_report),
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
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"relative-output-paths returned {result.returncode}, expected 0")
    outputs = _read_github_output(github_output)
    expected_paths = {
        "bom-path": output,
        "warning-report-path": warning_report,
        "summary-path": summary,
        "manifest-path": manifest,
        "error-report-path": error_report,
    }
    for key, path in expected_paths.items():
        if outputs.get(key) != path.as_posix():
            raise AssertionError(f"relative-output-paths {key} mismatch: {outputs.get(key)}")
    if outputs.get("status") != "success" or outputs.get("warning-count") != "0":
        raise AssertionError("relative-output-paths did not publish verified summary outputs")


def _run_stale_cleanup_failure_case(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    stale_output_directory = case_root / "bom.cdx.json"
    stale_output_directory.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTION_PATH": str(ROOT),
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_OUTPUT": str(github_output),
            "RUNNER_TEMP": str(case_root / "runner-temp"),
            "INPUT_MODEL_DIRECTORY": "tests/fixtures/complete-project",
            "INPUT_CONFIG": "tests/fixtures/complete-project/aibom.toml",
            "INPUT_FORMAT": "cyclonedx-json-1.7",
            "INPUT_OUTPUT": str(stale_output_directory),
            "INPUT_WARNING_REPORT": str(case_root / "warnings.json"),
            "INPUT_SUMMARY": str(case_root / "summary.json"),
            "INPUT_MANIFEST": str(case_root / "output-manifest.json"),
            "INPUT_ERROR_REPORT": str(case_root / "error.json"),
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
    if result.returncode != 70:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"stale-cleanup-failure returned {result.returncode}, expected 70")
    outputs = _read_github_output(github_output)
    if outputs.get("exit-code") != "70":
        raise AssertionError(f"stale-cleanup-failure exit-code mismatch: {outputs.get('exit-code')}")
    for key in ("warning-count", "status", "completeness-status", "format", "error-code", "error-stage"):
        if key in outputs:
            raise AssertionError(f"stale-cleanup-failure published untrusted output key: {key}")
    if "Could not remove a stale AI-BOM output" not in result.stderr:
        raise AssertionError("stale-cleanup-failure did not explain the cleanup failure")


def _run_stale_summary_failure_case(case_root: Path) -> None:
    case_root.mkdir(parents=True)
    github_output = case_root / "github-output.txt"
    output = case_root / "bom.cdx.json"
    warning_report = case_root / "warnings.json"
    summary = case_root / "summary.json"
    manifest = case_root / "output-manifest.json"
    error_report = case_root / "error.json"
    for path in (output, warning_report, summary, manifest, error_report):
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
            "INPUT_FORMAT": "unsupported-format",
            "INPUT_OUTPUT": str(output),
            "INPUT_WARNING_REPORT": str(warning_report),
            "INPUT_SUMMARY": str(summary),
            "INPUT_MANIFEST": str(manifest),
            "INPUT_ERROR_REPORT": str(error_report),
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
    for path in (output, warning_report, summary, manifest):
        if path.exists():
            raise AssertionError(f"stale-summary-failure left stale file: {path}")
    payload = json.loads(error_report.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "ai-bom-error-report/v1":
        raise AssertionError("stale-summary-failure did not replace the stale error report")
    if outputs.get("error-report-path") != error_report.as_posix():
        raise AssertionError("stale-summary-failure error-report-path mismatch")
    if outputs.get("error-code") != "EXPORTER_FAILURE" or outputs.get("error-stage") != "exporter":
        raise AssertionError("stale-summary-failure did not publish verified error metadata")


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
