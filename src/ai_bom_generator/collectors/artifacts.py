from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
from functools import lru_cache
import os
from pathlib import Path

from ai_bom_generator.config import LoadedConfig
from ai_bom_generator.domain.artifact import ModelArtifact
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.domain.warning import Warning
from ai_bom_generator.errors import CollectorError, InvalidInputError
from ai_bom_generator.hashing import sha256_file_snapshot
from ai_bom_generator.security import PathPolicy


_MAX_ARTIFACT_MATCHES_PER_PATTERN = 256
_MAX_ARTIFACT_SINGLE_FILE_BYTES = 16 * 1024 * 1024 * 1024
_MAX_ARTIFACT_TOTAL_BYTES = 25 * 1024 * 1024 * 1024
_DISCOVERED_ARTIFACT_PATTERNS = (
    "**/*.safetensors",
    "**/*.gguf",
    "**/*.bin",
    "**/*.pt",
    "**/*.pth",
    "**/*.ckpt",
    "**/*.onnx",
)
_DISCOVERED_ARTIFACT_EXCLUDES = (
    "**/.*/**",
    "**/.*",
    "**/.git/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
    "**/.cache/**",
    "**/.ruff_cache/**",
    "**/.mypy_cache/**",
)


@dataclass(frozen=True)
class _ArtifactPatternSpec:
    pattern: str
    source_field: str
    excludes: tuple[str, ...]
    discovery: bool


@dataclass
class _ArtifactPatternResult:
    spec: _ArtifactPatternSpec
    matches: list[Path] = field(default_factory=list)
    limit_exceeded: bool = False


def collect_artifacts(config: LoadedConfig, policy: PathPolicy, warnings: list[Warning]) -> list[ModelArtifact]:
    artifacts_config = config.get_table("artifacts")
    discovery = artifacts_config.get("discovery", False)
    if not isinstance(discovery, bool):
        raise InvalidInputError("[artifacts].discovery must be a boolean.", "config")

    includes = artifacts_config.get("include", [])
    if not includes and not discovery:
        warnings.append(
            Warning(
                code="MISSING_ARTIFACT_SELECTION",
                severity="warning",
                object_kind="artifact",
                object_id="artifacts",
                message="No model artifact include patterns were declared.",
                source=_source(config, "artifacts.include"),
                remediation="Add [artifacts].include patterns for model files to hash.",
            )
        )
        return []
    if not isinstance(includes, list) or any(not isinstance(item, str) for item in includes):
        raise InvalidInputError("[artifacts].include must be an array of strings.", "config")

    excludes = artifacts_config.get("exclude", [])
    if excludes and (not isinstance(excludes, list) or any(not isinstance(item, str) for item in excludes)):
        raise InvalidInputError("[artifacts].exclude must be an array of strings.", "config")

    include_patterns = [policy.validate_relative_glob(pattern, "[artifacts].include") for pattern in includes]
    discovery_patterns = list(_DISCOVERED_ARTIFACT_PATTERNS) if discovery else []
    exclude_patterns = [policy.validate_relative_glob(pattern, "[artifacts].exclude") for pattern in excludes]
    discovery_exclude_patterns = (
        exclude_patterns
        + [policy.validate_relative_glob(pattern, "[artifacts].discovery") for pattern in _DISCOVERED_ARTIFACT_EXCLUDES]
    )
    specs = _artifact_pattern_specs(
        include_patterns,
        discovery_patterns,
        exclude_patterns,
        discovery_exclude_patterns,
    )
    pattern_results = _scan_candidate_artifact_paths(policy.root, specs)

    selected: list[ModelArtifact] = []
    selected_paths: set[str] = set()
    selected_bytes = 0
    discovery_matched = False
    discovery_limit_hit = False
    for result in pattern_results:
        spec = result.spec
        if result.limit_exceeded:
            if spec.discovery:
                discovery_limit_hit = True
            warnings.append(
                Warning(
                    code="ARTIFACT_MATCH_LIMIT_EXCEEDED",
                    severity="warning",
                    object_kind="artifact",
                    object_id=spec.pattern,
                    message=(
                        "Artifact include pattern matched more than "
                        f"{_MAX_ARTIFACT_MATCHES_PER_PATTERN} candidate paths after excludes: {spec.pattern}"
                    ),
                    source=_source(config, spec.source_field),
                    remediation="Use narrower artifact include patterns or add exclude patterns for non-model files.",
                )
            )
            continue
        if not result.matches:
            if spec.discovery:
                continue
            warnings.append(
                Warning(
                    code="MISSING_ARTIFACT",
                    severity="warning",
                    object_kind="artifact",
                    object_id=spec.pattern,
                    message=f"No artifact matched include pattern: {spec.pattern}",
                    source=_source(config, spec.source_field),
                    remediation="Check the artifact path or remove the include pattern.",
                )
            )
            continue
        if spec.discovery:
            discovery_matched = True
        for match in result.matches:
            try:
                if match.is_symlink():
                    warnings.append(
                        Warning(
                            code="SKIPPED_SYMLINK",
                            severity="warning",
                            object_kind="artifact",
                            object_id=match.as_posix(),
                            message="Symlink artifact was skipped by default.",
                            source=_source(config, spec.source_field),
                            remediation="Use a real file inside the target root.",
                        )
                    )
                    continue
                resolved = match.resolve(strict=True)
                policy.ensure_inside_root(resolved)
                if not resolved.is_file():
                    continue
                relative_path = policy.relative_to_root(resolved)
                if relative_path in selected_paths:
                    continue
                artifact_bytes = _artifact_size(resolved)
                if _artifact_exceeds_single_file_budget(
                    config,
                    warnings,
                    relative_path,
                    artifact_bytes,
                    spec.source_field,
                ):
                    continue
                if _artifact_exceeds_total_budget(
                    config,
                    warnings,
                    relative_path,
                    selected_bytes,
                    artifact_bytes,
                    spec.source_field,
                ):
                    continue
                snapshot = sha256_file_snapshot(resolved)
                if _artifact_exceeds_single_file_budget(
                    config,
                    warnings,
                    relative_path,
                    snapshot.size,
                    spec.source_field,
                ):
                    continue
                if _artifact_exceeds_total_budget(
                    config,
                    warnings,
                    relative_path,
                    selected_bytes,
                    snapshot.size,
                    spec.source_field,
                ):
                    continue
                selected_paths.add(relative_path)
                selected_bytes += snapshot.size
                selected.append(
                    ModelArtifact(
                        path=relative_path,
                        size=snapshot.size,
                        digest=snapshot.digest,
                        digest_algorithm=snapshot.digest_algorithm,
                        selected_by=spec.pattern,
                        source=_source(config, spec.source_field),
                    )
                )
            except OSError as exc:
                raise CollectorError(f"Failed to collect artifact {match}: {exc}", "artifact") from exc
    if discovery and not discovery_matched and not discovery_limit_hit:
        warnings.append(
            Warning(
                code="MISSING_ARTIFACT",
                severity="warning",
                object_kind="artifact",
                object_id="artifacts.discovery",
                message="Artifact discovery did not match any default model artifact patterns.",
                source=_source(config, "artifacts.discovery"),
                remediation="Add explicit [artifacts].include patterns or place model artifacts under supported extensions.",
            )
        )
    return selected


def _artifact_pattern_specs(
    include_patterns: list[str],
    discovery_patterns: list[str],
    exclude_patterns: list[str],
    discovery_exclude_patterns: list[str],
) -> list[_ArtifactPatternSpec]:
    specs = [
        _ArtifactPatternSpec(pattern, "artifacts.include", tuple(exclude_patterns), False)
        for pattern in sorted(include_patterns)
    ]
    specs.extend(
        _ArtifactPatternSpec(pattern, "artifacts.discovery", tuple(discovery_exclude_patterns), True)
        for pattern in discovery_patterns
    )
    return specs


def _scan_candidate_artifact_paths(
    root: Path,
    specs: list[_ArtifactPatternSpec],
) -> list[_ArtifactPatternResult]:
    results = [_ArtifactPatternResult(spec) for spec in specs]
    if not results:
        return results

    for current_root, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current = Path(current_root)
        directory_names.sort()
        file_names.sort()
        entries = [*(current / name for name in directory_names), *(current / name for name in file_names)]

        for entry in entries:
            relative = entry.relative_to(root).as_posix()
            for result in results:
                if result.limit_exceeded:
                    continue
                if _is_excluded(entry, root, result.spec.excludes):
                    continue
                if not _matches_glob(relative, result.spec.pattern):
                    continue
                if len(result.matches) >= _MAX_ARTIFACT_MATCHES_PER_PATTERN:
                    result.matches.clear()
                    result.limit_exceeded = True
                    continue
                result.matches.append(entry)

        active_results = [result for result in results if not result.limit_exceeded]
        if not active_results:
            break
        directory_names[:] = [
            name
            for name in directory_names
            if (current / name).is_symlink()
            or not all(
                _is_excluded_subtree(current / name, root, result.spec.excludes)
                for result in active_results
            )
        ]

    for result in results:
        result.matches.sort()
    return results


def _artifact_exceeds_single_file_budget(
    config: LoadedConfig,
    warnings: list[Warning],
    relative_path: str,
    artifact_bytes: int,
    source_field: str,
) -> bool:
    if artifact_bytes > _MAX_ARTIFACT_SINGLE_FILE_BYTES:
        warnings.append(
            Warning(
                code="ARTIFACT_SIZE_LIMIT_EXCEEDED",
                severity="warning",
                object_kind="artifact",
                object_id=relative_path,
                message=(
                    f"Artifact exceeds the {_MAX_ARTIFACT_SINGLE_FILE_BYTES} byte "
                    f"single-file budget and was skipped: {relative_path} ({artifact_bytes} bytes)"
                ),
                source=_source(config, source_field),
                remediation="Hash a smaller staged artifact or wait for configurable budgets in a later release.",
            )
        )
        return True
    return False


def _artifact_exceeds_total_budget(
    config: LoadedConfig,
    warnings: list[Warning],
    relative_path: str,
    selected_bytes: int,
    artifact_bytes: int,
    source_field: str,
) -> bool:
    if selected_bytes + artifact_bytes > _MAX_ARTIFACT_TOTAL_BYTES:
        warnings.append(
            Warning(
                code="ARTIFACT_TOTAL_SIZE_LIMIT_EXCEEDED",
                severity="warning",
                object_kind="artifact",
                object_id=relative_path,
                message=(
                    f"Artifact would exceed the {_MAX_ARTIFACT_TOTAL_BYTES} byte total "
                    f"artifact budget and was skipped: {relative_path} "
                    f"({selected_bytes} selected bytes + {artifact_bytes} artifact bytes)"
                ),
                source=_source(config, source_field),
                remediation="Use narrower artifact patterns or run against a smaller staged artifact set.",
            )
        )
        return True
    return False


def _artifact_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise CollectorError(f"Failed to stat artifact {path}: {exc}", "artifact") from exc


def _is_excluded(path: Path, root: Path, excludes: tuple[str, ...]) -> bool:
    relative = path.relative_to(root).as_posix()
    return any(_matches_glob(relative, pattern) for pattern in excludes)


def _is_excluded_subtree(path: Path, root: Path, excludes: tuple[str, ...]) -> bool:
    relative = path.relative_to(root).as_posix()
    descendant = f"{relative}/__ai_bom_descendant__"
    return any(
        _matches_glob(relative, pattern) or _matches_glob(descendant, pattern)
        for pattern in excludes
    )


def _matches_glob(relative_path: str, pattern: str) -> bool:
    pattern_parts = _glob_parts(pattern)
    if not pattern_parts:
        return False
    path_parts = tuple(part for part in relative_path.replace("\\", "/").split("/") if part)

    @lru_cache(maxsize=None)
    def match(pattern_index: int, path_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        pattern_part = pattern_parts[pattern_index]
        if pattern_part == "**":
            return match(pattern_index + 1, path_index) or (
                path_index < len(path_parts) and match(pattern_index, path_index + 1)
            )
        return (
            path_index < len(path_parts)
            and fnmatch.fnmatchcase(path_parts[path_index], pattern_part)
            and match(pattern_index + 1, path_index + 1)
        )

    return match(0, 0)


@lru_cache(maxsize=512)
def _glob_parts(pattern: str) -> tuple[str, ...]:
    normalized = pattern.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return tuple(part for part in normalized.split("/") if part)


def _source(config: LoadedConfig, field: str) -> SourceLocation:
    path = config.path.as_posix() if config.path else "<inline-defaults>"
    return SourceLocation(path=path, field=field)
