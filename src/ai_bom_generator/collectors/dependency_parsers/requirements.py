from __future__ import annotations

import re
from urllib.parse import urlsplit

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

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


_INLINE_COMMENT_RE = re.compile(r"\s+#.*$")
_HASH_OPTION_RE = re.compile(r"(?:^|\s)--hash(?:=|\s+)(\S+)")
_URL_HASH_RE = re.compile(r"(?:^|&)([A-Za-z][A-Za-z0-9_-]*)=([^&]+)")
_URL_HASH_ALGORITHMS = frozenset({"blake2b", "blake2s", "md5", "sha1", "sha256", "sha384", "sha512"})


def parse_requirements(
    payload: bytes,
    relative_path: str,
    redactor: Redactor,
    limits: ParserLimits,
) -> DependencyParseResult:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DependencyParseError("requirements file is not valid UTF-8") from exc

    logical_lines = _logical_requirement_lines(text)
    if len(logical_lines) > limits.max_requirement_lines:
        raise DependencyFileLimitError(
            f"requirements file contains more than {limits.max_requirement_lines} logical lines"
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
        artifact_hashes = _requirement_artifact_hashes(
            raw_hashes,
            parsed.url,
            location,
            redactor,
            issues,
            limits,
        )
        source_locator = redactor.redact_text(parsed.url) if parsed.url else None
        revision = source_revision(parsed.url) if parsed.url else None
        packages.append(
            DependencyPackage(
                name=canonicalize_name(parsed.name),
                version=version,
                requirement=redactor.redact_text(str(parsed)),
                lockfile_format="requirements",
                package_source=DependencySourceEvidence(
                    source_type="url" if parsed.url else "requirement",
                    locator=source_locator,
                    revision=redactor.redact_text(revision) if revision else None,
                    artifact_hashes=artifact_hashes,
                ),
                marker=redactor.redact_text(marker) if marker else None,
                extras=tuple(sorted(parsed.extras)),
                source=SourceLocation(path=relative_path, field=location, collector="dependency"),
            )
        )
        if len(packages) > limits.max_packages:
            raise DependencyFileLimitError(
                f"dependency file contains more than {limits.max_packages} packages"
            )
    return parse_result(packages, issues)


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


def _requirement_artifact_hashes(
    raw_hashes: list[str],
    direct_url: str | None,
    location: str,
    redactor: Redactor,
    issues: list[DependencyParseIssue],
    limits: ParserLimits,
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
        parsed_hash = parse_artifact_hash(raw_hash, locator, redactor)
        if parsed_hash is None:
            issues.append(DependencyParseIssue(location, "artifact hash is invalid"))
            continue
        hashes.append(parsed_hash)
    return bounded_artifact_hashes(hashes, limits)
