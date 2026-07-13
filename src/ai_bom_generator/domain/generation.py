from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationMarkerEvidence:
    path: str
    digest: str
    digest_algorithm: str = "SHA-256"
