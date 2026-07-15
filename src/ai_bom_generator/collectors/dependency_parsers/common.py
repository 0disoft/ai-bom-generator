from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, urlsplit

from ai_bom_generator.domain.dependency import DependencyArtifactHash, DependencyPackage
from ai_bom_generator.security import Redactor


_HASH_VALUE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):([^\s:]+)$")


@dataclass(frozen=True)
class ParserLimits:
    max_packages: int
    max_requirement_lines: int
    max_artifact_hashes_per_package: int
    max_conda_lock_channels: int
    max_conda_lock_platforms: int
    max_conda_lock_yaml_depth: int
    max_pipenv_sources: int
    max_pipenv_json_depth: int


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


def parse_artifact_hash(
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


def bounded_artifact_hashes(
    hashes: list[DependencyArtifactHash],
    limits: ParserLimits,
) -> tuple[DependencyArtifactHash, ...]:
    unique = {artifact.identity_key(): artifact for artifact in hashes}
    if len(unique) > limits.max_artifact_hashes_per_package:
        raise DependencyFileLimitError(
            "dependency package contains more than "
            f"{limits.max_artifact_hashes_per_package} artifact hash records"
        )
    return tuple(sorted(unique.values(), key=lambda item: item.identity_key()))


def source_revision(locator: str) -> str | None:
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


def parse_result(
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
