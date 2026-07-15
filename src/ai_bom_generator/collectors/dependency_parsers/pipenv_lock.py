from __future__ import annotations

import json
from urllib.parse import urlsplit

from packaging.markers import InvalidMarker, Marker
from packaging.specifiers import InvalidSpecifier, SpecifierSet
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
)
from ai_bom_generator.domain.dependency import (
    DependencyArtifactHash,
    DependencyPackage,
    DependencySourceEvidence,
)
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.security import Redactor


_SUPPORTED_SPEC = 6
_GROUPS = ("default", "develop")
_SOURCE_KEYS = ("git", "file", "path")
_MARKER_KEYS = (
    "implementation_name",
    "implementation_version",
    "os_name",
    "platform_machine",
    "platform_python_implementation",
    "platform_release",
    "platform_system",
    "platform_version",
    "python_full_version",
    "python_version",
    "sys_platform",
)


class _DuplicateKeyError(ValueError):
    pass


def parse_pipenv_lock(
    payload: bytes,
    relative_path: str,
    redactor: Redactor,
    limits: ParserLimits,
) -> DependencyParseResult:
    try:
        document = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKeyError, RecursionError) as exc:
        raise DependencyParseError("Pipfile.lock is not valid duplicate-free UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise DependencyParseError("Pipfile.lock root must be an object")
    _validate_json_depth(document, limits.max_pipenv_json_depth)

    metadata = document.get("_meta")
    if not isinstance(metadata, dict):
        raise DependencyParseError("Pipfile.lock does not contain an _meta object")
    spec = metadata.get("pipfile-spec")
    if type(spec) is not int or spec != _SUPPORTED_SPEC:
        raise DependencyParseError(f"Pipfile.lock pipfile-spec must be {_SUPPORTED_SPEC}")

    issues: list[DependencyParseIssue] = []
    sources = _source_index(metadata.get("sources"), redactor, issues, limits)
    groups: list[tuple[str, dict[str, object]]] = []
    package_count = 0
    for group in _GROUPS:
        value = document.get(group)
        if value is None:
            continue
        if not isinstance(value, dict):
            issues.append(DependencyParseIssue(group, "dependency group is not an object"))
            continue
        groups.append((group, value))
        package_count += len(value)
    if not groups:
        raise DependencyParseError("Pipfile.lock does not contain default or develop dependencies")
    if package_count > limits.max_packages:
        raise DependencyFileLimitError(
            f"dependency file contains more than {limits.max_packages} packages"
        )

    for key, value in document.items():
        if key not in {"_meta", *_GROUPS} and isinstance(value, dict):
            issues.append(DependencyParseIssue(key, "dependency group is unsupported by pipfile-spec 6"))

    packages: list[DependencyPackage] = []
    for group, entries in groups:
        for raw_name, entry in entries.items():
            location = f"{group}.{raw_name}"
            package = _parse_package(raw_name, entry, location, relative_path, sources, redactor, issues, limits)
            if package is not None:
                packages.append(package)
    return parse_result(packages, issues)


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _validate_json_depth(value: object, limit: int, depth: int = 1) -> None:
    if depth > limit:
        raise DependencyFileLimitError(f"Pipfile.lock exceeds the {limit}-level JSON depth limit")
    if isinstance(value, dict):
        for item in value.values():
            _validate_json_depth(item, limit, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _validate_json_depth(item, limit, depth + 1)


def _source_index(
    value: object,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, list):
        issues.append(DependencyParseIssue("_meta.sources", "sources is not an array"))
        return {}
    if len(value) > limits.max_pipenv_sources:
        raise DependencyFileLimitError(
            f"Pipfile.lock contains more than {limits.max_pipenv_sources} package sources"
        )

    sources: dict[str, str] = {}
    for index, item in enumerate(value):
        location = f"_meta.sources[{index}]"
        if not isinstance(item, dict):
            issues.append(DependencyParseIssue(location, "source entry is not an object"))
            continue
        name = item.get("name")
        url = item.get("url")
        if not isinstance(name, str) or not name.strip():
            issues.append(DependencyParseIssue(f"{location}.name", "source name is invalid"))
            continue
        if not isinstance(url, str) or not url.strip():
            issues.append(DependencyParseIssue(f"{location}.url", "source URL is invalid"))
            continue
        normalized_name = name.strip()
        if normalized_name in sources:
            issues.append(DependencyParseIssue(f"{location}.name", "source name is duplicated"))
            continue
        sources[normalized_name] = redactor.redact_text(url.strip())
    return sources


def _parse_package(
    raw_name: object,
    entry: object,
    location: str,
    relative_path: str,
    sources: dict[str, str],
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
) -> DependencyPackage | None:
    if not isinstance(raw_name, str):
        issues.append(DependencyParseIssue(location, "package name is invalid"))
        return None
    try:
        name = canonicalize_name(raw_name, validate=True)
    except InvalidName:
        issues.append(DependencyParseIssue(location, "package name is not a valid Python distribution name"))
        return None
    if not isinstance(entry, dict):
        issues.append(DependencyParseIssue(location, "package entry is not an object"))
        return None

    extras = _extras(entry.get("extras"), location, redactor, issues)
    version, requirement = _version_requirement(name, extras, entry.get("version"), location, issues)
    source = _package_source(entry, location, sources, redactor, issues)
    source = DependencySourceEvidence(
        source_type=source.source_type,
        locator=source.locator,
        channel=source.channel,
        index=source.index,
        platform=source.platform,
        revision=source.revision,
        artifact_hashes=_artifact_hashes(entry.get("hashes"), location, redactor, issues, limits),
    )
    marker = _package_marker(entry, location, redactor, issues)
    return DependencyPackage(
        name=name,
        version=version,
        requirement=redactor.redact_text(requirement),
        lockfile_format="pipenv",
        package_source=source,
        marker=marker,
        extras=extras,
        source=SourceLocation(path=relative_path, field=location, collector="dependency"),
    )


def _extras(
    value: object,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        issues.append(DependencyParseIssue(f"{location}.extras", "package extras are not an array"))
        return ()
    extras: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(DependencyParseIssue(f"{location}.extras[{index}]", "package extra is invalid"))
            continue
        extras.add(redactor.redact_text(canonicalize_name(item.strip())))
    return tuple(sorted(extras))


def _version_requirement(
    name: str,
    extras: tuple[str, ...],
    value: object,
    location: str,
    issues: list[DependencyParseIssue],
) -> tuple[str | None, str]:
    base = name + (f"[{','.join(extras)}]" if extras else "")
    if value is None or value == "*":
        return None, base
    if not isinstance(value, str) or not value.strip():
        issues.append(DependencyParseIssue(f"{location}.version", "package version is invalid"))
        return None, base
    specifier = value.strip()
    try:
        parsed = SpecifierSet(specifier)
    except InvalidSpecifier:
        issues.append(DependencyParseIssue(f"{location}.version", "package version specifier is invalid"))
        return None, base
    exact = None
    if specifier.startswith("==") and not specifier.startswith("===") and "," not in specifier:
        candidate = specifier[2:].strip()
        if candidate and "*" not in candidate:
            exact = candidate
    return exact, f"{base}{parsed}"


def _package_source(
    entry: dict[str, object],
    location: str,
    sources: dict[str, str],
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> DependencySourceEvidence:
    selected = [key for key in _SOURCE_KEYS if key in entry]
    if len(selected) > 1:
        issues.append(DependencyParseIssue(location, "package declares multiple source types"))
        return DependencySourceEvidence(source_type="unknown")
    if selected:
        key = selected[0]
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(DependencyParseIssue(f"{location}.{key}", "source locator is invalid"))
            return DependencySourceEvidence(source_type=key)
        locator = redactor.redact_text(value.strip())
        if key == "git":
            revision = entry.get("ref")
            if revision is not None and (not isinstance(revision, str) or not revision.strip()):
                issues.append(DependencyParseIssue(f"{location}.ref", "Git source revision is invalid"))
                revision = None
            return DependencySourceEvidence(
                source_type="git",
                locator=locator,
                revision=redactor.redact_text(revision.strip()) if isinstance(revision, str) else None,
            )
        if key == "path":
            editable = entry.get("editable", False)
            if not isinstance(editable, bool):
                issues.append(DependencyParseIssue(f"{location}.editable", "editable flag is invalid"))
                editable = False
            return DependencySourceEvidence(source_type="editable" if editable else "path", locator=locator)
        scheme = urlsplit(value.strip()).scheme.lower()
        return DependencySourceEvidence(
            source_type="url" if scheme in {"http", "https"} else "file",
            locator=locator,
        )

    index = entry.get("index")
    if index is None:
        return DependencySourceEvidence(source_type="registry")
    if not isinstance(index, str) or not index.strip():
        issues.append(DependencyParseIssue(f"{location}.index", "package index is invalid"))
        return DependencySourceEvidence(source_type="registry")
    index_name = index.strip()
    index_url = sources.get(index_name)
    if index_url is None:
        issues.append(DependencyParseIssue(f"{location}.index", "package index is not declared in _meta.sources"))
        return DependencySourceEvidence(source_type="registry", index=redactor.redact_text(index_name))
    return DependencySourceEvidence(source_type="registry", locator=index_url, index=index_url)


def _package_marker(
    entry: dict[str, object],
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> str | None:
    expressions: list[str] = []
    explicit = entry.get("markers")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            issues.append(DependencyParseIssue(f"{location}.markers", "package marker is invalid"))
        else:
            expressions.append(explicit.strip())
    for key in _MARKER_KEYS:
        if key not in entry:
            continue
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(DependencyParseIssue(f"{location}.{key}", "package marker constraint is invalid"))
            continue
        expressions.append(f"{key} {value.strip()}")
    if not expressions:
        return None
    combined = expressions[0] if len(expressions) == 1 else " and ".join(f"({item})" for item in expressions)
    try:
        Marker(combined)
    except InvalidMarker:
        issues.append(DependencyParseIssue(f"{location}.markers", "combined package marker is invalid"))
        return None
    return redactor.redact_text(combined)


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
        issues.append(DependencyParseIssue(f"{location}.hashes", "package hashes are not an array"))
        return ()
    if len(value) > limits.max_artifact_hashes_per_package:
        raise DependencyFileLimitError(
            "dependency package contains more than "
            f"{limits.max_artifact_hashes_per_package} artifact hash records"
        )
    hashes: list[DependencyArtifactHash] = []
    for index, item in enumerate(value):
        parsed = parse_artifact_hash(item, None, redactor)
        if parsed is None:
            issues.append(DependencyParseIssue(f"{location}.hashes[{index}]", "artifact hash is invalid"))
            continue
        hashes.append(parsed)
    return bounded_artifact_hashes(hashes, limits)
