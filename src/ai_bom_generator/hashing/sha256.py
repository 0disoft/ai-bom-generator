from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from ai_bom_generator.errors import CollectorError


@dataclass(frozen=True)
class FileHashSnapshot:
    size: int
    digest: str
    digest_algorithm: str = "sha256"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    return sha256_file_snapshot(path, chunk_size).digest


def sha256_file_snapshot(path: Path, chunk_size: int = 1024 * 1024) -> FileHashSnapshot:
    if chunk_size <= 0:
        raise CollectorError("chunk_size must be positive for SHA-256 hashing.", "hash")

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            before = _snapshot_stat(handle.fileno())
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
            after = _snapshot_stat(handle.fileno())
    except OSError as exc:
        raise CollectorError(f"Failed to hash artifact {path}: {exc}", "hash") from exc
    if before != after:
        raise CollectorError(
            f"Artifact changed while hashing and cannot be represented as a stable snapshot: {path}",
            "hash",
        )
    return FileHashSnapshot(size=after.size, digest=digest.hexdigest())


@dataclass(frozen=True)
class _StableFileStat:
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int


def _snapshot_stat(file_descriptor: int) -> _StableFileStat:
    stat = os.fstat(file_descriptor)
    return _StableFileStat(
        device=stat.st_dev,
        inode=stat.st_ino,
        size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
        changed_ns=stat.st_ctime_ns,
    )
