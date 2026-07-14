from __future__ import annotations

import tomllib

from packaging.utils import InvalidName, canonicalize_name
from packaging.version import InvalidVersion, Version

from ai_bom_generator.collectors.dependency_parsers.common import (
    DependencyFileLimitError,
    DependencyParseError,
    DependencyParseIssue,
    DependencyParseResult,
    ParserLimits,
    bounded_artifact_hashes,
    parse_artifact_hash,
    parse_result,
)
from ai_bom_generator.domain.dependency import (
    DependencyArtifactHash,
    DependencyPackage,
    DependencySourceEvidence,
)
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.security import Redactor


_INDEX_SOURCE_TYPES = frozenset({"legacy"})
_KNOWN_SOURCE_TYPES = frozenset({"directory", "file", "git", "legacy", "url"})


def parse_poetry_lock(
    payload: bytes,
    relative_path: str,
    redactor: Redactor,
    limits: ParserLimits,
) -> DependencyParseResult:
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise DependencyParseError("poetry.lock is not valid UTF-8 TOML") from exc

    _validate_lock_version(document.get("metadata"))
    raw_packages = document.get("package")
    if not isinstance(raw_packages, list):
        raise DependencyParseError("poetry.lock does not contain a package array")
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
        if not isinstance(version, str) or not version.strip():
            issues.append(DependencyParseIssue(location, "package version is missing or invalid"))
            continue
        try:
            canonical_name = canonicalize_name(name, validate=True)
        except InvalidName:
            issues.append(
                DependencyParseIssue(location, "package name is not a valid Python distribution name")
            )
            continue

        marker = _package_marker(item.get("markers"), location, redactor, issues)
        normalized_version = version.strip()
        source = _package_source(item.get("source"), location, redactor, issues)
        source = DependencySourceEvidence(
            source_type=source.source_type,
            locator=source.locator,
            channel=source.channel,
            index=source.index,
            platform=source.platform,
            revision=source.revision,
            artifact_hashes=_artifact_hashes(
                item.get("files"),
                location,
                redactor,
                issues,
                limits,
            ),
        )
        packages.append(
            DependencyPackage(
                name=canonical_name,
                version=normalized_version,
                requirement=redactor.redact_text(f"{canonical_name}=={normalized_version}"),
                lockfile_format="poetry",
                package_source=source,
                marker=marker,
                extras=(),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
    return parse_result(packages, issues)


def _validate_lock_version(metadata: object) -> None:
    if not isinstance(metadata, dict):
        raise DependencyParseError("poetry.lock does not contain a metadata table")
    raw_version = metadata.get("lock-version")
    if not isinstance(raw_version, str):
        raise DependencyParseError("poetry.lock metadata lock-version is missing or invalid")
    try:
        lock_version = Version(raw_version)
    except InvalidVersion as exc:
        raise DependencyParseError("poetry.lock metadata lock-version is invalid") from exc
    if lock_version.major != 2:
        raise DependencyParseError("poetry.lock format major version must be 2")


def _package_marker(
    value: object,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return redactor.redact_text(value) if value else None
    if not isinstance(value, dict):
        issues.append(DependencyParseIssue(f"{location}.markers", "package markers are invalid"))
        return None

    markers: set[str] = set()
    for group, marker in value.items():
        if not isinstance(group, str) or not isinstance(marker, str) or not marker:
            issues.append(
                DependencyParseIssue(f"{location}.markers", "group-specific package markers are invalid")
            )
            return None
        markers.add(marker)
    if len(markers) == 1:
        return redactor.redact_text(next(iter(markers)))
    if markers:
        issues.append(
            DependencyParseIssue(
                f"{location}.markers",
                "group-specific package markers cannot be represented without a selected group",
            )
        )
    return None


def _package_source(
    value: object,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> DependencySourceEvidence:
    if value is None:
        return DependencySourceEvidence(source_type="registry")
    if not isinstance(value, dict):
        issues.append(DependencyParseIssue(f"{location}.source", "package source is not a table"))
        return DependencySourceEvidence(source_type="unknown")

    source_type = value.get("type")
    if not isinstance(source_type, str) or source_type not in _KNOWN_SOURCE_TYPES:
        issues.append(DependencyParseIssue(f"{location}.source.type", "package source type is unsupported"))
        return DependencySourceEvidence(source_type="unknown")
    raw_locator = value.get("url")
    if not isinstance(raw_locator, str) or not raw_locator.strip():
        issues.append(DependencyParseIssue(f"{location}.source.url", "package source URL is missing or invalid"))
        return DependencySourceEvidence(source_type=source_type)

    locator = redactor.redact_text(raw_locator.strip())
    revision = _source_revision(value, location, redactor, issues) if source_type == "git" else None
    return DependencySourceEvidence(
        source_type=source_type,
        locator=locator,
        index=locator if source_type in _INDEX_SOURCE_TYPES else None,
        revision=revision,
    )


def _source_revision(
    source: dict[object, object],
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> str | None:
    for field in ("resolved_reference", "reference"):
        value = source.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            issues.append(
                DependencyParseIssue(f"{location}.source.{field}", "git source revision is invalid")
            )
            continue
        return redactor.redact_text(value.strip())
    return None


def _artifact_hashes(
    value: object,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
) -> tuple[DependencyArtifactHash, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        issues.append(DependencyParseIssue(f"{location}.files", "package files are not an array"))
        return ()
    if len(value) > limits.max_artifact_hashes_per_package:
        raise DependencyFileLimitError(
            "dependency package contains more than "
            f"{limits.max_artifact_hashes_per_package} artifact file records"
        )

    hashes: list[DependencyArtifactHash] = []
    for index, item in enumerate(value):
        artifact_location = f"{location}.files[{index}]"
        if not isinstance(item, dict):
            issues.append(DependencyParseIssue(artifact_location, "artifact entry is not a table"))
            continue
        filename = item.get("file")
        if not isinstance(filename, str) or not filename.strip():
            issues.append(DependencyParseIssue(f"{artifact_location}.file", "artifact filename is invalid"))
            continue
        parsed_hash = parse_artifact_hash(item.get("hash"), filename.strip(), redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(f"{artifact_location}.hash", "artifact hash is invalid"))
            continue
        hashes.append(parsed_hash)
    return bounded_artifact_hashes(hashes, limits)
