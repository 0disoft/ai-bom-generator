from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


def main() -> int:
    action_root = _path_env("GITHUB_ACTION_PATH", Path(__file__).resolve().parents[1])
    workspace = _path_env("GITHUB_WORKSPACE", Path.cwd())
    runner_temp = _path_env("RUNNER_TEMP", Path(tempfile.gettempdir()))
    model_directory = _required_input("INPUT_MODEL_DIRECTORY")
    default_output_dir = runner_temp / "ai-bom-generator" / uuid.uuid4().hex
    output = _input_path("INPUT_OUTPUT", default_output_dir / "bom.cdx.json")
    warning_report = _input_path("INPUT_WARNING_REPORT", default_output_dir / "warnings.json")
    summary = _input_path("INPUT_SUMMARY", default_output_dir / "summary.json")
    manifest = _input_path("INPUT_MANIFEST", default_output_dir / "output-manifest.json")
    error_report = _input_path("INPUT_ERROR_REPORT", default_output_dir / "error.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    warning_report.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    error_report.parent.mkdir(parents=True, exist_ok=True)
    _remove_stale_action_outputs((output, warning_report, summary, manifest, error_report))

    args = [
        "uv",
        "run",
        "--project",
        str(action_root),
        "--locked",
        "--python",
        "3.12",
        "ai-bom",
        "generate",
        model_directory,
    ]
    config = os.environ.get("INPUT_CONFIG", "").strip()
    if config:
        args.extend(["--config", config])
    output_format = os.environ.get("INPUT_FORMAT", "").strip()
    if output_format:
        args.extend(["--format", output_format])
    args.extend(
        [
            "--output",
            str(output),
            "--warning-report",
            str(warning_report),
            "--summary",
            str(summary),
            "--manifest",
            str(manifest),
            "--error-report",
            str(error_report),
        ]
    )
    warnings = os.environ.get("INPUT_WARNINGS", "").strip()
    if warnings:
        args.extend(["--warnings", warnings])
    args.extend(["--redaction", _input_value("INPUT_REDACTION", "strict")])

    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(runner_temp / "ai-bom-generator-venv")
    env["UV_CACHE_DIR"] = str(runner_temp / "ai-bom-generator-uv-cache")
    result = subprocess.run(args, cwd=workspace, env=env)
    _write_outputs(output, warning_report, summary, manifest, error_report, result.returncode)
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


def _remove_stale_action_outputs(paths: tuple[Path, ...]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def _write_outputs(
    output: Path,
    warning_report: Path,
    summary: Path,
    manifest: Path,
    error_report: Path,
    exit_code: int,
) -> None:
    pairs = {
        "bom-path": output.as_posix(),
        "warning-report-path": warning_report.as_posix(),
        "summary-path": summary.as_posix(),
        "manifest-path": manifest.as_posix(),
        "error-report-path": error_report.as_posix(),
        "exit-code": str(exit_code),
    }
    payload = (
        _read_verified_summary(output, warning_report, summary, manifest)
        if exit_code in {0, 10}
        else {}
    )
    if payload:
        pairs.update(
            {
                "warning-count": str(payload.get("warning_count", "")),
                "status": str(payload.get("status", "")),
                "completeness-status": str(payload.get("completeness_status", "")),
                "format": str(payload.get("format", "")),
            }
        )
    error_payload = _read_verified_error_report(error_report, exit_code)
    if error_payload:
        error = error_payload.get("error")
        if isinstance(error, dict):
            pairs.update(
                {
                    "error-code": str(error.get("code", "")),
                    "error-stage": str(error.get("stage", "")),
                }
            )
    _append_github_outputs(pairs)


def _read_verified_error_report(path: Path, exit_code: int) -> dict[str, object]:
    if exit_code in {0, 10}:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("schema_version") != "ai-bom-error-report/v1":
        return {}
    if payload.get("status") != "failed" or payload.get("exit_code") != exit_code:
        return {}
    return payload


def _read_verified_summary(
    output: Path,
    warning_report: Path,
    summary: Path,
    manifest: Path,
) -> dict[str, object]:
    try:
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if manifest_payload.get("schema_version") != "ai-bom-output-manifest/v1":
        return {}
    if manifest_payload.get("status") != "committed":
        return {}
    files = manifest_payload.get("files")
    if not isinstance(files, list):
        return {}
    expected = {
        "bom": output,
        "warning_report": warning_report,
        "summary": summary,
    }
    by_role = {
        str(item.get("role")): item
        for item in files
        if isinstance(item, dict)
    }
    for role, path in expected.items():
        item = by_role.get(role)
        if item is None:
            return {}
        if item.get("path") != path.as_posix():
            return {}
        if not path.is_file():
            return {}
        if item.get("size_bytes") != path.stat().st_size:
            return {}
        if item.get("sha256") != _sha256_file(path):
            return {}
    try:
        payload = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_basic_outputs(exit_code: int) -> None:
    _append_github_outputs({"exit-code": str(exit_code)})


def _append_github_outputs(pairs: dict[str, str]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not github_output:
        return
    with Path(github_output).open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in pairs.items():
            delimiter = _output_delimiter(key, value)
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def _output_delimiter(key: str, value: str) -> str:
    base = f"AI_BOM_{key.replace('-', '_').upper()}_EOF"
    delimiter = base
    suffix = 1
    while delimiter in value:
        delimiter = f"{base}_{suffix}"
        suffix += 1
    return delimiter


if __name__ == "__main__":
    raise SystemExit(main())
