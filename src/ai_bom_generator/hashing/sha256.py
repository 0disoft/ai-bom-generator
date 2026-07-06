from __future__ import annotations

import hashlib
from pathlib import Path

from ai_bom_generator.errors import CollectorError


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise CollectorError(f"Failed to hash artifact {path}: {exc}", "hash") from exc
    return digest.hexdigest()
