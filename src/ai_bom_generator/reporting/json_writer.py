from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, TextIO
import uuid


JsonFilePayload = tuple[Path, Any]
JsonOutputPayload = tuple[str, Path, Any]


class OutputSetLockedError(RuntimeError):
    pass


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

        with _output_set_lock(manifest_path):
            _commit_staged_output_set(staged)
    finally:
        for _, temp_path, _ in staged:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _commit_staged_output_set(staged: list[tuple[str, Path, Path]]) -> None:
    backups: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for _, _, path in staged:
            if not path.exists():
                continue
            backup_path = _create_temp_path(path)
            backup_path.unlink()
            os.replace(path, backup_path)
            backups.append((backup_path, path))

        for _, temp_path, path in staged:
            os.replace(temp_path, path)
            replaced.append(path)
    except Exception:
        for path in replaced:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        for backup_path, path in reversed(backups):
            try:
                os.replace(backup_path, path)
            except OSError:
                pass
        raise
    finally:
        for backup_path, _ in backups:
            try:
                backup_path.unlink(missing_ok=True)
            except OSError:
                pass


@contextmanager
def _output_set_lock(manifest_path: Path):
    lock_path = manifest_path.with_name(f".{manifest_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            _lock_file(handle)
        except OSError as exc:
            raise OutputSetLockedError(f"Output set is already being committed: {manifest_path}") from exc
        try:
            yield
        finally:
            _unlock_file(handle)


def _lock_file(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
