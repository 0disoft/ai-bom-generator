from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from ai_bom_generator.collectors.dependency_parsers import (
    DependencyFileLimitError,
    DependencyParseError,
    DependencyParseIssue,
    DependencyParseResult,
    ParserLimits,
    parse_conda_lock,
    parse_requirements,
    parse_uv_lock,
)
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


def detect_dependency_format(relative_path: str, declared_type: object) -> str | None:
    if declared_type is not None:
        if not isinstance(declared_type, str):
            return None
        return _FORMAT_ALIASES.get(declared_type.strip().lower())

    name = Path(relative_path).name.lower()
    if name == "uv.lock":
        return "uv"
    if name in {"conda-lock.yml", "conda-lock.yaml"} or name.endswith(
        (".conda-lock.yml", ".conda-lock.yaml")
    ):
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
    return parser(payload, relative_path, redactor, _parser_limits())


def _parser_limits() -> ParserLimits:
    return ParserLimits(
        max_packages=MAX_DEPENDENCY_PACKAGES,
        max_requirement_lines=MAX_REQUIREMENT_LINES,
        max_artifact_hashes_per_package=MAX_ARTIFACT_HASH_RECORDS_PER_PACKAGE,
        max_conda_lock_channels=MAX_CONDA_LOCK_CHANNELS,
        max_conda_lock_platforms=MAX_CONDA_LOCK_PLATFORMS,
        max_conda_lock_yaml_depth=MAX_CONDA_LOCK_YAML_DEPTH,
    )


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


DependencyPayloadParser = Callable[[bytes, str, Redactor, ParserLimits], DependencyParseResult]

_DEPENDENCY_PARSERS: dict[str, DependencyPayloadParser] = {
    "conda-lock": parse_conda_lock,
    "uv": parse_uv_lock,
    "requirements": parse_requirements,
}

__all__ = [
    "DependencyFileLimitError",
    "DependencyParseError",
    "DependencyParseIssue",
    "DependencyParseResult",
    "detect_dependency_format",
    "parse_dependency_file",
]
