from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from urllib.parse import urlsplit

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import InvalidName, canonicalize_name

from ai_bom_generator.domain.dependency import DependencyPackage
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.security import Redactor


MAX_DEPENDENCY_FILE_BYTES = 4 * 1024 * 1024
MAX_DEPENDENCY_PACKAGES = 5_000
MAX_REQUIREMENT_LINES = 10_000

_FORMAT_ALIASES = {
    "pip": "requirements",
    "requirement": "requirements",
    "requirements": "requirements",
    "requirements.txt": "requirements",
    "uv": "uv",
    "uv-lock": "uv",
    "uv.lock": "uv",
}
_UV_SOURCE_KEYS = ("registry", "git", "url", "path", "editable", "virtual")
_INLINE_COMMENT_RE = re.compile(r"\s+#.*$")
_HASH_OPTION_RE = re.compile(r"\s+--hash(?:=|\s+)\S+")


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
    if dependency_format == "uv":
        return _parse_uv_lock(payload, relative_path, redactor)
    if dependency_format == "requirements":
        return _parse_requirements(payload, relative_path, redactor)
    raise DependencyParseError(f"Unsupported dependency format: {dependency_format}")


def _read_bounded_snapshot(path: Path) -> bytes:
    try:
        before = path.stat()
        if before.st_size > MAX_DEPENDENCY_FILE_BYTES:
            raise DependencyFileLimitError(
                f"dependency file exceeds the {MAX_DEPENDENCY_FILE_BYTES} byte read limit"
            )
        with path.open("rb") as handle:
            payload = handle.read(MAX_DEPENDENCY_FILE_BYTES + 1)
        after = path.stat()
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
        packages.append(
            DependencyPackage(
                name=canonical_name,
                version=normalized_version,
                requirement=redactor.redact_text(requirement),
                lockfile_format="uv",
                source_type=_uv_source_type(item.get("source")),
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
        packages.append(
            DependencyPackage(
                name=canonicalize_name(parsed.name),
                version=version,
                requirement=redactor.redact_text(str(parsed)),
                lockfile_format="requirements",
                source_type="url" if parsed.url else "requirement",
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


def _uv_source_type(source: object) -> str:
    if not isinstance(source, dict):
        return "unknown"
    for key in _UV_SOURCE_KEYS:
        if key in source:
            return key
    return "unknown"


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
