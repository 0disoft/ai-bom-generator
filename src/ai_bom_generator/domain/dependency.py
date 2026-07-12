from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.source_location import SourceLocation


@dataclass(frozen=True)
class DependencyPackage:
    name: str
    version: str | None
    requirement: str
    lockfile_format: str
    source_type: str
    source_locator: str | None
    marker: str | None
    extras: tuple[str, ...]
    source: SourceLocation

    def identity_key(self) -> str:
        return "\0".join(
            (
                self.source.path,
                self.name,
                self.version or "",
                self.requirement,
                self.lockfile_format,
                self.source_type,
                self.source_locator or "",
                self.marker or "",
                ",".join(self.extras),
            )
        )
