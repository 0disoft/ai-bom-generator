from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    action_root = _path_env("GITHUB_ACTION_PATH", Path(__file__).resolve().parents[1])
    workspace = _path_env("GITHUB_WORKSPACE", Path.cwd())
    runner_temp = _path_env("RUNNER_TEMP", Path(tempfile.gettempdir()))
    model_directory = _required_input("INPUT_MODEL_DIRECTORY")
    output = _input_path("INPUT_OUTPUT", runner_temp / "ai-bom-generator" / "bom.cdx.json")
    warning_report = _input_path("INPUT_WARNING_REPORT", runner_temp / "ai-bom-generator" / "warnings.json")
    summary = _input_path("INPUT_SUMMARY", runner_temp / "ai-bom-generator" / "summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    warning_report.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "uv",
        "run",
        "--project",
        str(action_root),
        "--python",
        "3.12",
        "ai-bom",
        "generate",
        model_directory,
    ]
    config = os.environ.get("INPUT_CONFIG", "").strip()
    if config:
        args.extend(["--config", config])
    args.extend(
        [
            "--format",
            _input_value("INPUT_FORMAT", "cyclonedx-json-1.7"),
            "--output",
            str(output),
            "--warning-report",
            str(warning_report),
            "--summary",
            str(summary),
            "--warnings",
            _input_value("INPUT_WARNINGS", "allow"),
            "--redaction",
            _input_value("INPUT_REDACTION", "strict"),
        ]
    )

    env = os.environ.copy()
    env.setdefault("UV_PROJECT_ENVIRONMENT", str(runner_temp / "ai-bom-generator-venv"))
    result = subprocess.run(args, cwd=workspace, env=env)
    _write_outputs(output, warning_report, summary, result.returncode)
    return result.returncode


def _required_input(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        _write_basic_outputs(exit_code=20)
        print(f"{name} is required.", file=sys.stderr)
        raise SystemExit(20)
    return value


def _input_value(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def _input_path(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else default


def _path_env(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else default


def _write_outputs(output: Path, warning_report: Path, summary: Path, exit_code: int) -> None:
    pairs = {
        "bom-path": output.as_posix(),
        "warning-report-path": warning_report.as_posix(),
        "summary-path": summary.as_posix(),
        "exit-code": str(exit_code),
    }
    if summary.is_file():
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        pairs.update(
            {
                "warning-count": str(payload.get("warning_count", "")),
                "completeness-status": str(payload.get("status", "")),
                "format": str(payload.get("format", "")),
            }
        )
    _append_github_outputs(pairs)


def _write_basic_outputs(exit_code: int) -> None:
    _append_github_outputs({"exit-code": str(exit_code)})


def _append_github_outputs(pairs: dict[str, str]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not github_output:
        return
    with Path(github_output).open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in pairs.items():
            handle.write(f"{key}={value}\n")


if __name__ == "__main__":
    raise SystemExit(main())
