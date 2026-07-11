from __future__ import annotations

import argparse
import base64
import binascii
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
DEFAULT_REPOSITORY = "0disoft/ai-bom-generator"
DEFAULT_SMOKE_REPOSITORY = "0disoft/ai-bom-generator-action-smoke"
DEFAULT_SMOKE_WORKFLOW = "AI-BOM Smoke"
DEFAULT_SMOKE_WORKFLOW_PATH = ".github/workflows/ai-bom-smoke.yml"
DEFAULT_PYTHON = "3.12"
DEFAULT_CONSOLE = "ai-bom"
REQUIRED_PACKAGE_TYPES = {"bdist_wheel", "sdist"}
LEGACY_MUTABLE_RELEASE_TAGS = frozenset(
    {"v0.1.0", "v0.1.1", "v0.1.2", "v0.1.4", "v0.2.0"}
)


def main(argv: list[str] | None = None) -> int:
    project = _read_project_metadata()
    parser = argparse.ArgumentParser(description="Verify an AI-BOM Generator release after publishing.")
    parser.add_argument("--package", default=str(project["name"]), help="PyPI package name to verify.")
    parser.add_argument("--version", default=str(project["version"]), help="Published package version to verify.")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub repository in owner/name form.")
    parser.add_argument("--tag", help="GitHub release tag. Defaults to v<version>.")
    parser.add_argument("--publish-run-id", help="GitHub Actions run id for the PyPI publish workflow.")
    parser.add_argument("--smoke-repository", default=DEFAULT_SMOKE_REPOSITORY, help="External smoke repository.")
    parser.add_argument("--smoke-workflow", default=DEFAULT_SMOKE_WORKFLOW, help="External smoke workflow name.")
    parser.add_argument(
        "--smoke-workflow-path",
        default=DEFAULT_SMOKE_WORKFLOW_PATH,
        help="External smoke workflow path used to verify the exact version action ref.",
    )
    parser.add_argument("--smoke-run-id", help="External smoke workflow run id. Defaults to latest run.")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="Python version passed to uv for install smoke.")
    parser.add_argument("--console", default=DEFAULT_CONSOLE, help="Installed console script command.")
    args = parser.parse_args(argv)

    tag = args.tag or f"v{args.version}"
    try:
        _validate_semver_tag(tag, args.version)
        _verify_pypi(args.package, args.version)
        _verify_install_smoke(args.package, args.version, args.python, args.console)
        _verify_github_release(args.repository, tag)
        if args.publish_run_id:
            _verify_github_run(args.repository, args.publish_run_id, expected_head_branch=tag, label="publish")
        if args.smoke_repository:
            _verify_external_smoke(
                args.smoke_repository,
                args.smoke_workflow,
                args.smoke_workflow_path,
                args.smoke_run_id,
                args.repository,
                tag,
            )
    except ReleaseVerificationError as error:
        print(f"release verification failed: {error}", file=sys.stderr)
        return 1

    print(f"release verification passed: {args.package} {args.version} ({tag})")
    return 0


class ReleaseVerificationError(Exception):
    pass


def _read_project_metadata() -> dict[str, object]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ReleaseVerificationError("pyproject.toml is missing [project] metadata")
    return project


def _validate_semver_tag(tag: str, version: str) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ReleaseVerificationError(f"release tag must be strict vMAJOR.MINOR.PATCH, got {tag!r}")
    if tag != f"v{version}":
        raise ReleaseVerificationError(f"release tag {tag!r} does not match version {version!r}")


def _verify_pypi(package: str, version: str) -> None:
    project_payload = _fetch_json(f"https://pypi.org/pypi/{package}/json")
    info = project_payload.get("info")
    if not isinstance(info, dict):
        raise ReleaseVerificationError("PyPI project JSON is missing info")
    actual_name = info.get("name")
    if _normalize_package_name(str(actual_name)) != _normalize_package_name(package):
        raise ReleaseVerificationError(f"PyPI project name mismatch: expected {package!r}, got {actual_name!r}")

    version_payload = _fetch_json(f"https://pypi.org/pypi/{package}/{version}/json")
    version_info = version_payload.get("info")
    if not isinstance(version_info, dict):
        raise ReleaseVerificationError(f"PyPI {package} {version} JSON is missing info")
    version_name = version_info.get("name")
    version_number = version_info.get("version")
    if _normalize_package_name(str(version_name)) != _normalize_package_name(package):
        raise ReleaseVerificationError(
            f"PyPI version project name mismatch: expected {package!r}, got {version_name!r}"
        )
    if version_number != version:
        raise ReleaseVerificationError(
            f"PyPI version endpoint mismatch: expected {version!r}, got {version_number!r}"
        )
    urls = version_payload.get("urls")
    if not isinstance(urls, list):
        raise ReleaseVerificationError(f"PyPI {package} {version} JSON is missing urls")
    package_types = {str(url.get("packagetype")) for url in urls if isinstance(url, dict)}
    missing = REQUIRED_PACKAGE_TYPES - package_types
    if missing:
        raise ReleaseVerificationError(f"PyPI {package} {version} is missing package types: {', '.join(sorted(missing))}")


def _verify_install_smoke(package: str, version: str, python: str, console: str) -> None:
    with tempfile.TemporaryDirectory(prefix="ai-bom-release-") as temp:
        result = _run(
            [
                "uv",
                "run",
                "--python",
                python,
                "--with",
                f"{package}=={version}",
                console,
                "--help",
            ],
            cwd=Path(temp),
        )
    if result.returncode != 0:
        raise ReleaseVerificationError(f"install smoke failed for {package}=={version}")
    if "generate" not in result.stdout:
        raise ReleaseVerificationError(f"install smoke help output did not include the generate command for {console}")


def _verify_github_release(repository: str, tag: str) -> None:
    payload = _gh_json(
        [
            "release",
            "view",
            tag,
            "--repo",
            repository,
            "--json",
            "tagName,isDraft,isPrerelease,isImmutable,url,publishedAt",
        ]
    )
    if payload.get("tagName") != tag:
        raise ReleaseVerificationError(f"GitHub Release tag mismatch: expected {tag!r}, got {payload.get('tagName')!r}")
    if payload.get("isDraft"):
        raise ReleaseVerificationError(f"GitHub Release {tag} is still a draft")
    if payload.get("isPrerelease"):
        raise ReleaseVerificationError(f"GitHub Release {tag} is marked prerelease")
    if not payload.get("isImmutable") and tag not in LEGACY_MUTABLE_RELEASE_TAGS:
        raise ReleaseVerificationError(f"GitHub Release {tag} is not immutable")


def _verify_external_smoke(
    repository: str,
    workflow: str,
    workflow_path: str,
    run_id: str | None,
    action_repository: str,
    expected_tag: str,
) -> None:
    resolved_run_id = run_id or _latest_workflow_run_id(repository, workflow)
    run = _github_run_payload(repository, resolved_run_id)
    _verify_run_payload(run, label="external smoke")
    if run.get("workflowName") != workflow:
        raise ReleaseVerificationError(
            f"external smoke run workflow mismatch: expected {workflow!r}, got {run.get('workflowName')!r}"
        )
    head_sha = run.get("headSha")
    if not isinstance(head_sha, str) or not head_sha:
        raise ReleaseVerificationError("external smoke run is missing headSha")
    _verify_smoke_action_ref(
        repository,
        workflow_path,
        head_sha,
        action_repository,
        expected_tag,
    )


def _latest_workflow_run_id(repository: str, workflow: str) -> str:
    payload = _gh_json(
        [
            "run",
            "list",
            "--repo",
            repository,
            "--workflow",
            workflow,
            "--limit",
            "1",
            "--json",
            "databaseId",
        ]
    )
    if not isinstance(payload, list) or not payload:
        raise ReleaseVerificationError(f"no workflow runs found for {repository} workflow {workflow!r}")
    run = payload[0]
    if not isinstance(run, dict) or run.get("databaseId") is None:
        raise ReleaseVerificationError(f"unexpected GitHub run payload for {repository}: {run!r}")
    return str(run["databaseId"])


def _verify_smoke_action_ref(
    repository: str,
    workflow_path: str,
    head_sha: str,
    action_repository: str,
    expected_tag: str,
) -> None:
    normalized_path = quote(workflow_path.strip("/"), safe="/")
    encoded_sha = quote(head_sha, safe="")
    payload = _gh_json(["api", f"repos/{repository}/contents/{normalized_path}?ref={encoded_sha}"])
    if not isinstance(payload, dict) or payload.get("encoding") != "base64":
        raise ReleaseVerificationError("external smoke workflow content is not base64 encoded")
    encoded_content = payload.get("content")
    if not isinstance(encoded_content, str):
        raise ReleaseVerificationError("external smoke workflow content is missing")
    try:
        workflow_text = base64.b64decode("".join(encoded_content.split()), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ReleaseVerificationError("external smoke workflow content is not valid base64 UTF-8") from error

    action_prefix = f"{action_repository}@"
    action_uses: list[str] = []
    for line in workflow_text.splitlines():
        match = re.match(r"^-?\s*uses:\s*([^\s#]+)", line.strip())
        if match:
            value = match.group(1).strip("\"'")
            if value.startswith(action_prefix):
                action_uses.append(value)
    expected_use = f"{action_repository}@{expected_tag}"
    if action_uses != [expected_use]:
        actual = ", ".join(action_uses) if action_uses else "missing"
        raise ReleaseVerificationError(
            f"external smoke workflow must use exactly {expected_use!r} at run commit {head_sha}; got {actual}"
        )


def _verify_github_run(
    repository: str,
    run_id: str,
    expected_head_branch: str | None = None,
    label: str = "workflow",
) -> None:
    payload = _github_run_payload(repository, run_id)
    _verify_run_payload(payload, expected_head_branch=expected_head_branch, label=label)


def _github_run_payload(repository: str, run_id: str) -> dict[str, object]:
    payload = _gh_json(
        [
            "run",
            "view",
            run_id,
            "--repo",
            repository,
            "--json",
            "status,conclusion,url,headBranch,headSha,event,workflowName",
        ]
    )
    if not isinstance(payload, dict):
        raise ReleaseVerificationError(f"unexpected GitHub run payload for {repository}: {payload!r}")
    return payload


def _verify_run_payload(
    payload: dict[str, object],
    expected_head_branch: str | None = None,
    label: str = "workflow",
) -> None:
    if payload.get("status") != "completed":
        raise ReleaseVerificationError(f"{label} run is not completed: {payload.get('url')}")
    if payload.get("conclusion") != "success":
        raise ReleaseVerificationError(f"{label} run did not succeed: {payload.get('url')}")
    if expected_head_branch is not None and payload.get("headBranch") != expected_head_branch:
        raise ReleaseVerificationError(
            f"{label} run head branch mismatch: expected {expected_head_branch!r}, got {payload.get('headBranch')!r}"
        )


def _fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ai-bom-generator-release-verifier"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ReleaseVerificationError(f"{url} returned HTTP {error.code}") from error
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise ReleaseVerificationError(f"failed to read JSON from {url}: {error}") from error
    if not isinstance(payload, dict):
        raise ReleaseVerificationError(f"{url} did not return a JSON object")
    return payload


def _gh_json(args: list[str]) -> object:
    result = _run(["gh", *args], cwd=ROOT)
    if result.returncode != 0:
        raise ReleaseVerificationError(f"gh {' '.join(args)} failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ReleaseVerificationError(f"gh {' '.join(args)} returned invalid JSON") from error


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


if __name__ == "__main__":
    raise SystemExit(main())
