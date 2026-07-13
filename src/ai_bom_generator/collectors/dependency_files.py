from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib
from typing import Callable
from urllib.parse import parse_qs, urlsplit

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import InvalidName, canonicalize_name
import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node

from ai_bom_generator.domain.dependency import (
    DependencyArtifactHash,
    DependencyPackage,
    DependencySourceEvidence,
)
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.security import Redactor, open_binary_nofollow


MAX_DEPENDENCY_FILE_BYTES = 4 * 1024 * 1024
MAX_DEPENDENCY_PACKAGES = 5_000
MAX_REQUIREMENT_LINES = 10_000
MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE = 256
MAX_CONDA_LOCK_CHANNELS = 128
MAX_CONDA_LOCK_PLATFORMS = 64
MAX_CONDA_LOCK_YAML_DEPTH = 64

_FORMAT_ALIASES = {
    "pip": "requirements",
    "requirement": "requirements",
    "requirements": "requirements",
    "requirements.txt": "requirements",
    "conda-lock": "conda-lock",
    "conda-lock.yml": "conda-lock",
    "conda-lock.yaml": "conda-lock",
    "uv": "uv",
    "uv-lock": "uv",
    "uv.lock": "uv",
}
_UV_SOURCE_KEYS = ("registry", "git", "url", "path", "editable", "virtual")
_INLINE_COMMENT_RE = re.compile(r"\s+#.*$")
_HASH_OPTION_RE = re.compile(r"(?:^|\s)--hash(?:=|\s+)(\S+)")
_HASH_VALUE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):([^\s:]+)$")
_URL_HASH_RE = re.compile(r"(?:^|&)([A-Za-z][A-Za-z0-9_-]*)=([^&]+)")
_URL_HASH_ALGORITHMS = frozenset({"blake2b", "blake2s", "md5", "sha1", "sha256", "sha384", "sha512"})
_CONDA_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CONDA_LOCK_HASH_RE = {
    "md5": re.compile(r"^[0-9a-fA-F]{32}$"),
    "sha256": re.compile(r"^[0-9a-fA-F]{64}$"),
}


class _CondaLockLoader(yaml.SafeLoader):
    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._compose_depth = 0

    def compose_node(self, parent: Node | None, index: int | None) -> Node:
        if self.check_event(AliasEvent):
            raise yaml.YAMLError("conda-lock YAML aliases are not supported")
        self._compose_depth += 1
        try:
            if self._compose_depth > MAX_CONDA_LOCK_YAML_DEPTH:
                raise yaml.YAMLError(
                    f"conda-lock YAML exceeds the {MAX_CONDA_LOCK_YAML_DEPTH} level nesting limit"
                )
            return super().compose_node(parent, index)
        finally:
            self._compose_depth -= 1

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[object, object]:
        if not isinstance(node, MappingNode):
            raise yaml.YAMLError("conda-lock mapping node is invalid")
        seen: set[object] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in seen
            except TypeError as exc:
                raise yaml.YAMLError("conda-lock mapping keys must be scalar") from exc
            if duplicate:
                raise yaml.YAMLError(f"conda-lock YAML contains duplicate key: {key}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


@dataclass(frozen=True)
class DependencyParseIssue:
    location: str
    reason: str


@dataclass(frozen=True)
class DependencyParseResult:
    packages: tuple[DependencyPackage, ...]
    skipped_entries: int = 0
    first_issue: DependencyParseIssue | None = None


class DependencyParseError(ValueError):
    pass


class DependencyFileLimitError(DependencyParseError):
    pass


def detect_dependency_format(relative_path: str, declared_type: object) -> str | None:
    if declared_type is not None:
        if not isinstance(declared_type, str):
            return None
        return _FORMAT_ALIASES.get(declared_type.strip().lower())

    name = Path(relative_path).name.lower()
    if name == "uv.lock":
        return "uv"
    if name in {"conda-lock.yml", "conda-lock.yaml"} or name.endswith((".conda-lock.yml", ".conda-lock.yaml")):
        return "conda-lock"
    if name == "requirements.lock" or (name.startswith("requirements") and name.endswith(".txt")):
        return "requirements"
    return None


def parse_dependency_file(
    path: Path,
    relative_path: str,
    dependency_format: str,
    redactor: Redactor,
) -> DependencyParseResult:
    payload = _read_bounded_snapshot(path)
    parser = _DEPENDENCY_PARSERS.get(dependency_format)
    if parser is None:
        raise DependencyParseError(f"Unsupported dependency format: {dependency_format}")
    return parser(payload, relative_path, redactor)


def _read_bounded_snapshot(path: Path) -> bytes:
    try:
        with open_binary_nofollow(path) as handle:
            before = os.fstat(handle.fileno())
            if before.st_size > MAX_DEPENDENCY_FILE_BYTES:
                raise DependencyFileLimitError(
                    f"dependency file exceeds the {MAX_DEPENDENCY_FILE_BYTES} byte read limit"
                )
            payload = handle.read(MAX_DEPENDENCY_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
    except DependencyFileLimitError:
        raise
    except OSError as exc:
        raise DependencyParseError("dependency file could not be read") from exc

    if len(payload) > MAX_DEPENDENCY_FILE_BYTES:
        raise DependencyFileLimitError(
            f"dependency file exceeds the {MAX_DEPENDENCY_FILE_BYTES} byte read limit"
        )
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    if before_identity != after_identity:
        raise DependencyParseError("dependency file changed while it was being read")
    return payload


def _parse_uv_lock(payload: bytes, relative_path: str, redactor: Redactor) -> DependencyParseResult:
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise DependencyParseError("uv.lock is not valid UTF-8 TOML") from exc

    raw_packages = document.get("package")
    if not isinstance(raw_packages, list):
        raise DependencyParseError("uv.lock does not contain a package array")
    if len(raw_packages) > MAX_DEPENDENCY_PACKAGES:
        raise DependencyFileLimitError(
            f"dependency file contains more than {MAX_DEPENDENCY_PACKAGES} packages"
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
            issues.append(DependencyParseIssue(location, "package name is not a valid Python distribution name"))
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
            artifact_hashes=_uv_artifact_hashes(item, location, redactor, issues),
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
    return _result(packages, issues)


def _parse_requirements(payload: bytes, relative_path: str, redactor: Redactor) -> DependencyParseResult:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DependencyParseError("requirements file is not valid UTF-8") from exc

    logical_lines = _logical_requirement_lines(text)
    if len(logical_lines) > MAX_REQUIREMENT_LINES:
        raise DependencyFileLimitError(
            f"requirements file contains more than {MAX_REQUIREMENT_LINES} logical lines"
        )

    packages: list[DependencyPackage] = []
    issues: list[DependencyParseIssue] = []
    for line_number, raw_requirement in logical_lines:
        location = f"line:{line_number}"
        requirement_text = _INLINE_COMMENT_RE.sub("", raw_requirement).strip()
        raw_hashes = _HASH_OPTION_RE.findall(requirement_text)
        requirement_text = _HASH_OPTION_RE.sub("", requirement_text).strip()
        if not requirement_text:
            continue
        if requirement_text.startswith("-"):
            issues.append(DependencyParseIssue(location, "pip directive is not followed"))
            continue
        try:
            parsed = Requirement(requirement_text)
        except InvalidRequirement:
            issues.append(DependencyParseIssue(location, "entry is not a valid PEP 508 requirement"))
            continue
        if parsed.url and urlsplit(parsed.url).scheme.lower() in {"", "file"}:
            issues.append(DependencyParseIssue(location, "local direct reference is not collected"))
            continue

        version = _exact_pinned_version(parsed)
        marker = str(parsed.marker) if parsed.marker is not None else None
        artifact_hashes = _requirement_artifact_hashes(raw_hashes, parsed.url, location, redactor, issues)
        source_locator = redactor.redact_text(parsed.url) if parsed.url else None
        source_revision = _source_revision(parsed.url) if parsed.url else None
        packages.append(
            DependencyPackage(
                name=canonicalize_name(parsed.name),
                version=version,
                requirement=redactor.redact_text(str(parsed)),
                lockfile_format="requirements",
                package_source=DependencySourceEvidence(
                    source_type="url" if parsed.url else "requirement",
                    locator=source_locator,
                    revision=redactor.redact_text(source_revision) if source_revision else None,
                    artifact_hashes=artifact_hashes,
                ),
                marker=redactor.redact_text(marker) if marker else None,
                extras=tuple(sorted(parsed.extras)),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
        if len(packages) > MAX_DEPENDENCY_PACKAGES:
            raise DependencyFileLimitError(
                f"dependency file contains more than {MAX_DEPENDENCY_PACKAGES} packages"
            )
    return _result(packages, issues)


def _parse_conda_lock(payload: bytes, relative_path: str, redactor: Redactor) -> DependencyParseResult:
    try:
        text = payload.decode("utf-8")
        document = yaml.load(text, Loader=_CondaLockLoader)
    except (UnicodeDecodeError, yaml.YAMLError, RecursionError) as exc:
        raise DependencyParseError("conda-lock file is not valid bounded UTF-8 YAML") from exc

    if not isinstance(document, dict):
        raise DependencyParseError("conda-lock file root is not a mapping")
    version = document.get("version")
    if isinstance(version, bool) or version != 1:
        raise DependencyParseError("conda-lock file version must be 1")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise DependencyParseError("conda-lock file does not contain a metadata mapping")
    channels = _conda_lock_channels(metadata.get("channels"), redactor)
    platforms = _conda_lock_platforms(metadata.get("platforms"))

    raw_packages = document.get("package")
    if not isinstance(raw_packages, list):
        raise DependencyParseError("conda-lock file does not contain a package array")
    if len(raw_packages) > MAX_DEPENDENCY_PACKAGES:
        raise DependencyFileLimitError(
            f"dependency file contains more than {MAX_DEPENDENCY_PACKAGES} packages"
        )

    packages: list[DependencyPackage] = []
    issues: list[DependencyParseIssue] = []
    for index, item in enumerate(raw_packages):
        location = f"package[{index}]"
        if not isinstance(item, dict):
            issues.append(DependencyParseIssue(location, "package entry is not a mapping"))
            continue

        name = _conda_lock_required_string(item, "name", location, issues)
        version_value = _conda_lock_required_string(item, "version", location, issues)
        manager = _conda_lock_required_string(item, "manager", location, issues)
        platform = _conda_lock_required_string(item, "platform", location, issues)
        locator = _conda_lock_required_string(item, "url", location, issues)
        if None in {name, version_value, manager, platform, locator}:
            continue
        assert name is not None
        assert version_value is not None
        assert manager is not None
        assert platform is not None
        assert locator is not None

        if manager not in {"conda", "pip"}:
            issues.append(DependencyParseIssue(f"{location}.manager", "package manager is unsupported"))
            continue
        if platform not in platforms:
            issues.append(DependencyParseIssue(f"{location}.platform", "package platform is not declared in metadata"))
            continue
        if not _is_remote_dependency_locator(locator):
            issues.append(DependencyParseIssue(f"{location}.url", "local or relative package URL is not collected"))
            continue

        normalized_name = _conda_lock_package_name(name, manager)
        if normalized_name is None:
            issues.append(DependencyParseIssue(f"{location}.name", "package name is invalid for its manager"))
            continue
        artifact_hashes = _conda_lock_artifact_hashes(
            item.get("hash"),
            manager,
            locator,
            location,
            redactor,
            issues,
        )
        if artifact_hashes is None:
            continue

        redacted_locator = redactor.redact_text(locator)
        source_revision = _source_revision(locator) if manager == "pip" else None
        packages.append(
            DependencyPackage(
                name=normalized_name,
                version=version_value,
                requirement=redactor.redact_text(f"{normalized_name}=={version_value}"),
                lockfile_format="conda-lock",
                package_source=DependencySourceEvidence(
                    source_type=manager,
                    locator=redacted_locator,
                    channel=_conda_lock_channel_for(locator, channels) if manager == "conda" else None,
                    platform=redactor.redact_text(platform),
                    revision=redactor.redact_text(source_revision) if source_revision else None,
                    artifact_hashes=artifact_hashes,
                ),
                marker=None,
                extras=(),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
    return _result(packages, issues)


def _conda_lock_channels(
    value: object,
    redactor: Redactor,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise DependencyParseError("conda-lock metadata channels must be an array")
    if len(value) > MAX_CONDA_LOCK_CHANNELS:
        raise DependencyFileLimitError(
            f"conda-lock metadata contains more than {MAX_CONDA_LOCK_CHANNELS} channels"
        )
    channels: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        raw_channel = item if isinstance(item, str) else item.get("url") if isinstance(item, dict) else None
        if not isinstance(raw_channel, str) or not raw_channel.strip():
            raise DependencyParseError(f"conda-lock metadata channel[{index}] is invalid")
        normalized = raw_channel.strip().rstrip("/")
        channels.append((normalized, redactor.redact_text(normalized)))
    return tuple(channels)


def _conda_lock_platforms(value: object) -> frozenset[str]:
    if not isinstance(value, list):
        raise DependencyParseError("conda-lock metadata platforms must be an array")
    if len(value) > MAX_CONDA_LOCK_PLATFORMS:
        raise DependencyFileLimitError(
            f"conda-lock metadata contains more than {MAX_CONDA_LOCK_PLATFORMS} platforms"
        )
    platforms: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise DependencyParseError(f"conda-lock metadata platform[{index}] is invalid")
        platforms.add(item.strip())
    return frozenset(platforms)


def _conda_lock_required_string(
    package: dict[object, object],
    field: str,
    location: str,
    issues: list[DependencyParseIssue],
) -> str | None:
    value = package.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(DependencyParseIssue(f"{location}.{field}", f"package {field} is missing or invalid"))
        return None
    return value.strip()


def _conda_lock_package_name(name: str, manager: str) -> str | None:
    if manager == "pip":
        try:
            return canonicalize_name(name, validate=True)
        except InvalidName:
            return None
    if _CONDA_PACKAGE_NAME_RE.fullmatch(name) is None:
        return None
    return name


def _conda_lock_artifact_hashes(
    value: object,
    manager: str,
    locator: str,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> tuple[DependencyArtifactHash, ...] | None:
    if not isinstance(value, dict):
        issues.append(DependencyParseIssue(f"{location}.hash", "package hash is not a mapping"))
        return None
    unsupported_keys = sorted(str(key) for key in value if key not in {"md5", "sha256"})
    if unsupported_keys:
        issues.append(DependencyParseIssue(f"{location}.hash", "package hash contains unsupported algorithms"))
        return None

    hashes: list[DependencyArtifactHash] = []
    for algorithm in ("md5", "sha256"):
        raw_hash = value.get(algorithm)
        if raw_hash is None:
            continue
        if not isinstance(raw_hash, str) or _CONDA_LOCK_HASH_RE[algorithm].fullmatch(raw_hash) is None:
            issues.append(DependencyParseIssue(f"{location}.hash.{algorithm}", "package hash is invalid"))
            return None
        parsed_hash = _parse_artifact_hash(f"{algorithm}:{raw_hash}", locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(f"{location}.hash.{algorithm}", "package hash is invalid"))
            return None
        hashes.append(parsed_hash)
    if manager == "conda" and not any(item.algorithm == "md5" for item in hashes):
        issues.append(DependencyParseIssue(f"{location}.hash.md5", "conda package MD5 hash is required"))
        return None
    return _bounded_artifact_hashes(hashes)


def _conda_lock_channel_for(
    locator: str,
    channels: tuple[tuple[str, str], ...],
) -> str | None:
    parsed = urlsplit(locator)
    path = parsed.path.replace("\\", "/")
    matches: list[tuple[int, str]] = []
    for raw_channel, redacted_channel in channels:
        channel_parts = urlsplit(raw_channel)
        if channel_parts.scheme:
            if locator == raw_channel or locator.startswith(f"{raw_channel}/"):
                matches.append((len(raw_channel), redacted_channel))
            continue
        channel_name = raw_channel.strip("/")
        if (
            channel_name
            and parsed.hostname is not None
            and parsed.hostname.lower() == "conda.anaconda.org"
            and path.startswith(f"/{channel_name}/")
        ):
            matches.append((len(channel_name), redacted_channel))
    if not matches:
        return None
    return max(matches, key=lambda item: item[0])[1]


def _is_remote_dependency_locator(locator: str) -> bool:
    parsed = urlsplit(locator)
    return bool(parsed.scheme and parsed.scheme.lower() != "file" and parsed.netloc)


def _logical_requirement_lines(text: str) -> list[tuple[int, str]]:
    logical: list[tuple[int, str]] = []
    parts: list[str] = []
    start_line = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not parts and (not stripped or stripped.startswith("#")):
            continue
        if not parts:
            start_line = line_number
        if stripped.endswith("\\"):
            parts.append(stripped[:-1].rstrip())
            continue
        parts.append(stripped)
        logical.append((start_line, " ".join(part for part in parts if part)))
        parts = []
    if parts:
        logical.append((start_line, " ".join(part for part in parts if part)))
    return logical


def _exact_pinned_version(requirement: Requirement) -> str | None:
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1:
        return None
    specifier = specifiers[0]
    if specifier.operator not in {"==", "==="} or "*" in specifier.version:
        return None
    return specifier.version


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
                issues.append(DependencyParseIssue(f"{location}.source.{key}", "source locator is not a string"))
                return DependencySourceEvidence(source_type=key)
            locator = redactor.redact_text(value)
            source_revision = _source_revision(value) if key == "git" else None
            return DependencySourceEvidence(
                source_type=key,
                locator=locator,
                index=locator if key == "registry" else None,
                revision=redactor.redact_text(source_revision) if source_revision else None,
            )
    issues.append(DependencyParseIssue(f"{location}.source", "package source type is unsupported"))
    return DependencySourceEvidence(source_type="unknown")


def _uv_artifact_hashes(
    package: dict[str, object],
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
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
        parsed_hash = _parse_artifact_hash(raw_hash, locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(f"{artifact_location}.hash", "artifact hash is invalid"))
            continue
        hashes.append(parsed_hash)
    return _bounded_artifact_hashes(hashes)


def _requirement_artifact_hashes(
    raw_hashes: list[str],
    direct_url: str | None,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
) -> tuple[DependencyArtifactHash, ...]:
    candidates: list[tuple[str, str | None]] = [(raw_hash, None) for raw_hash in raw_hashes]
    if direct_url:
        fragment = urlsplit(direct_url).fragment
        candidates.extend(
            (f"{algorithm}:{value}", direct_url)
            for algorithm, value in _URL_HASH_RE.findall(fragment)
            if algorithm.lower() in _URL_HASH_ALGORITHMS
        )

    hashes: list[DependencyArtifactHash] = []
    for raw_hash, locator in candidates:
        parsed_hash = _parse_artifact_hash(raw_hash, locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(location, "artifact hash is invalid"))
            continue
        hashes.append(parsed_hash)
    return _bounded_artifact_hashes(hashes)


def _parse_artifact_hash(
    raw_hash: object,
    locator: str | None,
    redactor: Redactor,
) -> DependencyArtifactHash | None:
    if not isinstance(raw_hash, str):
        return None
    match = _HASH_VALUE_RE.fullmatch(raw_hash.strip())
    if match is None:
        return None
    return DependencyArtifactHash(
        algorithm=match.group(1).lower(),
        value=redactor.redact_text(match.group(2)),
        locator=redactor.redact_text(locator) if locator else None,
    )


def _bounded_artifact_hashes(
    hashes: list[DependencyArtifactHash],
) -> tuple[DependencyArtifactHash, ...]:
    unique = {artifact.identity_key(): artifact for artifact in hashes}
    if len(unique) > MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE:
        raise DependencyFileLimitError(
            "dependency package contains more than "
            f"{MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE} artifact hash records"
        )
    return tuple(sorted(unique.values(), key=lambda item: item.identity_key()))


def _source_revision(locator: str) -> str | None:
    parsed = urlsplit(locator)
    if parsed.fragment and "=" not in parsed.fragment:
        return parsed.fragment
    query = parse_qs(parsed.query, keep_blank_values=False)
    for key in ("rev", "tag", "branch", "revision"):
        values = query.get(key)
        if values and values[0]:
            return values[0]
    if parsed.scheme.startswith("git+") and "@" in parsed.path:
        revision = parsed.path.rsplit("@", 1)[1]
        return revision or None
    return None


def _result(
    packages: list[DependencyPackage],
    issues: list[DependencyParseIssue],
) -> DependencyParseResult:
    unique: dict[str, DependencyPackage] = {}
    for package in packages:
        unique.setdefault(package.identity_key(), package)
    ordered = tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.source.path,
                item.name,
                item.version or "",
                item.requirement,
            ),
        )
    )
    return DependencyParseResult(
        packages=ordered,
        skipped_entries=len(issues),
        first_issue=issues[0] if issues else None,
    )


DependencyPayloadParser = Callable[[bytes, str, Redactor], DependencyParseResult]

_DEPENDENCY_PARSERS: dict[str, DependencyPayloadParser] = {
    "conda-lock": _parse_conda_lock,
    "uv": _parse_uv_lock,
    "requirements": _parse_requirements,
}
