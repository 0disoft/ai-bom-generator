from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Callable

from ai_bom_generator.config import LoadedConfig
from ai_bom_generator.domain.generation import GenerationMarkerEvidence
from ai_bom_generator.errors import CollectorError, InvalidInputError
from ai_bom_generator.security import PathPolicy, open_binary_nofollow


MAX_GENERATION_MARKER_BYTES = 4 * 1024


@dataclass(frozen=True)
class GenerationMarkerSnapshot:
    payload: bytes
    evidence: GenerationMarkerEvidence


def collect_initial_generation_marker(
    config: LoadedConfig,
    policy: PathPolicy,
) -> GenerationMarkerSnapshot | None:
    marker_path = _configured_marker_path(config)
    if marker_path is None:
        return None
    resolved = policy.resolve_existing_file(marker_path, required=True)
    return _read_and_validate_marker(
        resolved,
        policy,
        lambda message: InvalidInputError(message, "generation-marker"),
    )


def verify_final_generation_marker(
    config: LoadedConfig,
    policy: PathPolicy,
    initial: GenerationMarkerSnapshot | None,
) -> GenerationMarkerEvidence | None:
    if initial is None:
        return None
    marker_path = _configured_marker_path(config)
    if marker_path is None:
        raise CollectorError("Configured generation marker disappeared during collection.", "generation-marker")
    try:
        resolved = policy.resolve_existing_file(marker_path, required=True)
    except InvalidInputError as exc:
        raise CollectorError(f"Generation marker became unavailable during collection: {exc.message}", "generation-marker") from exc
    final = _read_and_validate_marker(
        resolved,
        policy,
        lambda message: CollectorError(message, "generation-marker"),
    )
    if final.payload != initial.payload:
        raise CollectorError(
            "Generation marker changed during collection; collected files may not belong to one producer generation.",
            "generation-marker",
        )
    return final.evidence


def _configured_marker_path(config: LoadedConfig) -> str | None:
    generation = config.get_table("generation")
    marker = generation.get("marker")
    if marker is None:
        return None
    if not isinstance(marker, str) or not marker.strip():
        raise InvalidInputError("[generation].marker must be a non-empty string.", "config")
    return marker


def _read_and_validate_marker(
    path: Path,
    policy: PathPolicy,
    error_factory: Callable[[str], Exception],
) -> GenerationMarkerSnapshot:
    try:
        with open_binary_nofollow(path) as handle:
            before = os.fstat(handle.fileno())
            if before.st_size > MAX_GENERATION_MARKER_BYTES:
                raise OSError(f"generation marker exceeds the {MAX_GENERATION_MARKER_BYTES} byte read limit")
            payload = handle.read(MAX_GENERATION_MARKER_BYTES + 1)
            after = os.fstat(handle.fileno())
        if len(payload) > MAX_GENERATION_MARKER_BYTES:
            raise OSError(f"generation marker exceeds the {MAX_GENERATION_MARKER_BYTES} byte read limit")
        if _file_snapshot(before) != _file_snapshot(after):
            raise OSError("generation marker changed while it was being read")
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        _validate_marker_data(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise error_factory(f"Invalid generation marker {path}: {exc}") from exc

    relative_path = policy.relative_to_root(path)
    return GenerationMarkerSnapshot(
        payload=payload,
        evidence=GenerationMarkerEvidence(path=relative_path, digest=sha256(payload).hexdigest()),
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _validate_marker_data(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("marker root must be an object")
    expected_keys = {"schema_version", "generation", "state"}
    if set(data) != expected_keys:
        raise ValueError("marker must contain only schema_version, generation, and state")
    if data["schema_version"] != "1":
        raise ValueError('schema_version must be "1"')
    if not isinstance(data["generation"], str) or not data["generation"].strip():
        raise ValueError("generation must be a non-empty string")
    if data["state"] != "complete":
        raise ValueError('state must be "complete"')


def _file_snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
