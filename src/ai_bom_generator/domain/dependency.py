from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.source_location import SourceLocation


@dataclass(frozen=True)
class DependencyArtifactHash:
    algorithm: str
    value: str
    locator: str | None = None

    def identity_key(self) -> str:
        return "\0".join((self.algorithm, self.value, self.locator or ""))


@dataclass(frozen=True)
class DependencySourceEvidence:
    source_type: str
    locator: str | None = None
    channel: str | None = None
    index: str | None = None
    platform: str | None = None
    revision: str | None = None
    artifact_hashes: tuple[DependencyArtifactHash, ...] = ()

    def identity_key(self) -> str:
        return "\0".join(
            (
                self.source_type,
                self.locator or "",
                self.channel or "",
                self.index or "",
                self.platform or "",
                self.revision or "",
                *(artifact.identity_key() for artifact in self.artifact_hashes),
            )
        )


@dataclass(frozen=True)
class DependencyPackage:
    name: str
    version: str | None
    requirement: str
    lockfile_format: str
    package_source: DependencySourceEvidence
    marker: str | None
    extras: tuple[str, ...]
    source: SourceLocation

    @property
    def source_type(self) -> str:
        return self.package_source.source_type

    @property
    def source_locator(self) -> str | None:
        return self.package_source.locator

    def identity_key(self) -> str:
        return "\0".join(
            (
                self.source.path,
                self.name,
                self.version or "",
                self.requirement,
                self.lockfile_format,
                self.package_source.identity_key(),
                self.marker or "",
                ",".join(self.extras),
            )
        )
