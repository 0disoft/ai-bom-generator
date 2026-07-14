from __future__ import annotations

import re
from urllib.parse import urlsplit

from packaging.utils import InvalidName, canonicalize_name
import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node

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


_CONDA_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CONDA_LOCK_HASH_RE = {
    "md5": re.compile(r"^[0-9a-fA-F]{32}$"),
    "sha256": re.compile(r"^[0-9a-fA-F]{64}$"),
}


def parse_conda_lock(
    payload: bytes,
    relative_path: str,
    redactor: Redactor,
    limits: ParserLimits,
) -> DependencyParseResult:
    try:
        text = payload.decode("utf-8")
        document = yaml.load(text, Loader=_conda_lock_loader(limits.max_conda_lock_yaml_depth))
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
    channels = _conda_lock_channels(metadata.get("channels"), redactor, limits)
    platforms = _conda_lock_platforms(metadata.get("platforms"), limits)

    raw_packages = document.get("package")
    if not isinstance(raw_packages, list):
        raise DependencyParseError("conda-lock file does not contain a package array")
    if len(raw_packages) > limits.max_packages:
        raise DependencyFileLimitError(
            f"dependency file contains more than {limits.max_packages} packages"
        )

    packages: list[DependencyPackage] = []
    issues: list[DependencyParseIssue] = []
    for index, item in enumerate(raw_packages):
        location = f"package[{index}]"
        if not isinstance(item, dict):
            issues.append(DependencyParseIssue(location, "package entry is not a mapping"))
            continue

        name = _required_string(item, "name", location, issues)
        version_value = _required_string(item, "version", location, issues)
        manager = _required_string(item, "manager", location, issues)
        platform = _required_string(item, "platform", location, issues)
        locator = _required_string(item, "url", location, issues)
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
            issues.append(
                DependencyParseIssue(f"{location}.platform", "package platform is not declared in metadata")
            )
            continue
        if not _is_remote_dependency_locator(locator):
            issues.append(
                DependencyParseIssue(f"{location}.url", "local or relative package URL is not collected")
            )
            continue

        normalized_name = _package_name(name, manager)
        if normalized_name is None:
            issues.append(
                DependencyParseIssue(f"{location}.name", "package name is invalid for its manager")
            )
            continue
        artifact_hashes = _artifact_hashes(
            item.get("hash"),
            manager,
            locator,
            location,
            redactor,
            issues,
            limits,
        )
        if artifact_hashes is None:
            continue

        redacted_locator = redactor.redact_text(locator)
        revision = source_revision(locator) if manager == "pip" else None
        packages.append(
            DependencyPackage(
                name=normalized_name,
                version=version_value,
                requirement=redactor.redact_text(f"{normalized_name}=={version_value}"),
                lockfile_format="conda-lock",
                package_source=DependencySourceEvidence(
                    source_type=manager,
                    locator=redacted_locator,
                    channel=_channel_for(locator, channels) if manager == "conda" else None,
                    platform=redactor.redact_text(platform),
                    revision=redactor.redact_text(revision) if revision else None,
                    artifact_hashes=artifact_hashes,
                ),
                marker=None,
                extras=(),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
    return parse_result(packages, issues)


def _conda_lock_loader(max_depth: int) -> type[yaml.SafeLoader]:
    class CondaLockLoader(yaml.SafeLoader):
        def __init__(self, stream: str) -> None:
            super().__init__(stream)
            self._compose_depth = 0

        def compose_node(self, parent: Node | None, index: int | None) -> Node:
            if self.check_event(AliasEvent):
                raise yaml.YAMLError("conda-lock YAML aliases are not supported")
            self._compose_depth += 1
            try:
                if self._compose_depth > max_depth:
                    raise yaml.YAMLError(
                        f"conda-lock YAML exceeds the {max_depth} level nesting limit"
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

    return CondaLockLoader


def _conda_lock_channels(
    value: object,
    redactor: Redactor,
    limits: ParserLimits,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise DependencyParseError("conda-lock metadata channels must be an array")
    if len(value) > limits.max_conda_lock_channels:
        raise DependencyFileLimitError(
            f"conda-lock metadata contains more than {limits.max_conda_lock_channels} channels"
        )
    channels: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        raw_channel = item if isinstance(item, str) else item.get("url") if isinstance(item, dict) else None
        if not isinstance(raw_channel, str) or not raw_channel.strip():
            raise DependencyParseError(f"conda-lock metadata channel[{index}] is invalid")
        normalized = raw_channel.strip().rstrip("/")
        channels.append((normalized, redactor.redact_text(normalized)))
    return tuple(channels)


def _conda_lock_platforms(value: object, limits: ParserLimits) -> frozenset[str]:
    if not isinstance(value, list):
        raise DependencyParseError("conda-lock metadata platforms must be an array")
    if len(value) > limits.max_conda_lock_platforms:
        raise DependencyFileLimitError(
            f"conda-lock metadata contains more than {limits.max_conda_lock_platforms} platforms"
        )
    platforms: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise DependencyParseError(f"conda-lock metadata platform[{index}] is invalid")
        platforms.add(item.strip())
    return frozenset(platforms)


def _required_string(
    package: dict[object, object],
    field: str,
    location: str,
    issues: list[DependencyParseIssue],
) -> str | None:
    value = package.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(
            DependencyParseIssue(f"{location}.{field}", f"package {field} is missing or invalid")
        )
        return None
    return value.strip()


def _package_name(name: str, manager: str) -> str | None:
    if manager == "pip":
        try:
            return canonicalize_name(name, validate=True)
        except InvalidName:
            return None
    if _CONDA_PACKAGE_NAME_RE.fullmatch(name) is None:
        return None
    return name


def _artifact_hashes(
    value: object,
    manager: str,
    locator: str,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
) -> tuple[DependencyArtifactHash, ...] | None:
    if not isinstance(value, dict):
        issues.append(DependencyParseIssue(f"{location}.hash", "package hash is not a mapping"))
        return None
    unsupported_keys = sorted(str(key) for key in value if key not in {"md5", "sha256"})
    if unsupported_keys:
        issues.append(
            DependencyParseIssue(f"{location}.hash", "package hash contains unsupported algorithms")
        )
        return None

    hashes: list[DependencyArtifactHash] = []
    for algorithm in ("md5", "sha256"):
        raw_hash = value.get(algorithm)
        if raw_hash is None:
            continue
        if not isinstance(raw_hash, str) or _CONDA_LOCK_HASH_RE[algorithm].fullmatch(raw_hash) is None:
            issues.append(DependencyParseIssue(f"{location}.hash.{algorithm}", "package hash is invalid"))
            return None
        parsed_hash = parse_artifact_hash(f"{algorithm}:{raw_hash}", locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(f"{location}.hash.{algorithm}", "package hash is invalid"))
            return None
        hashes.append(parsed_hash)
    if manager == "conda" and not any(item.algorithm == "md5" for item in hashes):
        issues.append(DependencyParseIssue(f"{location}.hash.md5", "conda package MD5 hash is required"))
        return None
    return bounded_artifact_hashes(hashes, limits)


def _channel_for(
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
