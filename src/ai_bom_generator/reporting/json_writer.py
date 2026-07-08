from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, TextIO
import uuid


JsonFilePayload = tuple[Path, Any]
JsonOutputPayload = tuple[str, Path, Any]


def write_json_file(path: Path, payload: Any) -> None:
    write_json_files_atomically([(path, payload)])


def write_json_files_atomically(items: Iterable[JsonFilePayload]) -> None:
    staged: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for path, payload in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = _create_temp_path(path)
            staged.append((temp_path, path))
            _write_temp_json_file(temp_path, payload)
        for temp_path, path in staged:
            os.replace(temp_path, path)
            replaced.append(path)
    except Exception:
        for path in replaced:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    finally:
        for temp_path, _ in staged:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def write_json_output_set(items: Iterable[JsonOutputPayload], manifest_path: Path) -> None:
    staged: list[tuple[str, Path, Path]] = []
    replaced: list[Path] = []
    try:
        for role, path, payload in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = _create_temp_path(path)
            staged.append((role, temp_path, path))
            _write_temp_json_file(temp_path, payload)

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_temp_path = _create_temp_path(manifest_path)
        manifest_payload = _build_output_manifest(staged)
        staged.append(("manifest", manifest_temp_path, manifest_path))
        _write_temp_json_file(manifest_temp_path, manifest_payload)

        for _, temp_path, path in staged:
            os.replace(temp_path, path)
            replaced.append(path)
    except Exception:
        for path in replaced:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    finally:
        for _, temp_path, _ in staged:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def write_json_stream(stream: TextIO, payload: Any) -> None:
    stream.write(_stable_json(payload))
    stream.write("\n")


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _build_output_manifest(staged: list[tuple[str, Path, Path]]) -> dict[str, object]:
    return {
        "schema_version": "ai-bom-output-manifest/v1",
        "generation_id": uuid.uuid4().hex,
        "status": "committed",
        "files": [
            {
                "role": role,
                "path": final_path.as_posix(),
                "sha256": _sha256_file(temp_path),
                "size_bytes": temp_path.stat().st_size,
            }
            for role, temp_path, final_path in staged
        ],
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _create_temp_path(path: Path) -> Path:
    handle, name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    os.close(handle)
    return Path(name)


def _write_temp_json_file(path: Path, payload: Any) -> None:
    text = _stable_json(payload)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
