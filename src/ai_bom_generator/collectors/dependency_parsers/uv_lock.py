from __future__ import annotations

import tomllib

from packaging.utils import InvalidName, canonicalize_name

from ai_bom_generator.collectors.dependency_parsers.common import (
    DependencyFileLimitError,
    DependencyParseError,
    DependencyParseIssue,
    DependencyParseResult,
    ParserLimits,
    bounded_artifact_hashes,
    parse_artifact_hash,
    parse_result,
    source_revision,
)
from ai_bom_generator.domain.dependency import (
    DependencyArtifactHash,
    DependencyPackage,
    DependencySourceEvidence,
)
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.security import Redactor


_UV_SOURCE_KEYS = ("registry", "git", "url", "path", "editable", "virtual")


def parse_uv_lock(
    payload: bytes,
    relative_path: str,
    redactor: Redactor,
    limits: ParserLimits,
) -> DependencyParseResult:
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise DependencyParseError("uv.lock is not valid UTF-8 TOML") from exc

    raw_packages = document.get("package")
    if not isinstance(raw_packages, list):
        raise DependencyParseError("uv.lock does not contain a package array")
    if len(raw_packages) > limits.max_packages:
        raise DependencyFileLimitError(
            f"dependency file contains more than {limits.max_packages} packages"
        )

    packages: list[DependencyPackage] = []
    issues: list[DependencyParseIssue] = []
    for index, item in enumerate(raw_packages):
        location = f"package[{index}]"
        if not isinstance(item, dict):
            issues.append(DependencyParseIssue(location, "package entry is not a table"))
            continue
        name = item.get("name")
        version = item.get("version")
        if not isinstance(name, str) or not name.strip():
            issues.append(DependencyParseIssue(location, "package name is missing or invalid"))
            continue
        if version is not None and not isinstance(version, str):
            issues.append(DependencyParseIssue(location, "package version is not a string"))
            continue

        try:
            canonical_name = canonicalize_name(name, validate=True)
        except InvalidName:
            issues.append(
                DependencyParseIssue(location, "package name is not a valid Python distribution name")
            )
            continue
        normalized_version = version.strip() if isinstance(version, str) and version.strip() else None
        requirement = canonical_name
        if normalized_version:
            requirement = f"{canonical_name}=={normalized_version}"
        package_source = _uv_source(item.get("source"), location, redactor, issues)
        package_source = DependencySourceEvidence(
            source_type=package_source.source_type,
            locator=package_source.locator,
            channel=package_source.channel,
            index=package_source.index,
            platform=package_source.platform,
            revision=package_source.revision,
            artifact_hashes=_uv_artifact_hashes(item, location, redactor, issues, limits),
        )
        packages.append(
            DependencyPackage(
                name=canonical_name,
                version=normalized_version,
                requirement=redactor.redact_text(requirement),
                lockfile_format="uv",
                package_source=package_source,
                marker=None,
                extras=(),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
    return parse_result(packages, issues)


def _uv_source(
    source: object,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> DependencySourceEvidence:
    if source is None:
        return DependencySourceEvidence(source_type="unknown")
    if not isinstance(source, dict):
        issues.append(DependencyParseIssue(f"{location}.source", "package source is not a table"))
        return DependencySourceEvidence(source_type="unknown")
    for key in _UV_SOURCE_KEYS:
        if key in source:
            value = source.get(key)
            if not isinstance(value, str):
                issues.append(
                    DependencyParseIssue(f"{location}.source.{key}", "source locator is not a string")
                )
                return DependencySourceEvidence(source_type=key)
            locator = redactor.redact_text(value)
            revision = source_revision(value) if key == "git" else None
            return DependencySourceEvidence(
                source_type=key,
                locator=locator,
                index=locator if key == "registry" else None,
                revision=redactor.redact_text(revision) if revision else None,
            )
    issues.append(DependencyParseIssue(f"{location}.source", "package source type is unsupported"))
    return DependencySourceEvidence(source_type="unknown")


def _uv_artifact_hashes(
    package: dict[str, object],
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
) -> tuple[DependencyArtifactHash, ...]:
    artifacts: list[tuple[str, object]] = []
    if "sdist" in package:
        artifacts.append((f"{location}.sdist", package.get("sdist")))
    if "wheels" in package:
        wheels = package.get("wheels")
        if isinstance(wheels, list):
            artifacts.extend((f"{location}.wheels[{index}]", item) for index, item in enumerate(wheels))
        else:
            issues.append(DependencyParseIssue(f"{location}.wheels", "wheels is not an array"))

    hashes: list[DependencyArtifactHash] = []
    for artifact_location, artifact in artifacts:
        if not isinstance(artifact, dict):
            issues.append(DependencyParseIssue(artifact_location, "artifact entry is not a table"))
            continue
        raw_hash = artifact.get("hash")
        if raw_hash is None:
            continue
        locator = artifact.get("url")
        if locator is not None and not isinstance(locator, str):
            issues.append(DependencyParseIssue(f"{artifact_location}.url", "artifact URL is not a string"))
            locator = None
        parsed_hash = parse_artifact_hash(raw_hash, locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(f"{artifact_location}.hash", "artifact hash is invalid"))
            continue
        hashes.append(parsed_hash)
    return bounded_artifact_hashes(hashes, limits)
