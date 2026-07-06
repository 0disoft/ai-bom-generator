from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.source_location import SourceLocation


@dataclass(frozen=True, order=True)
class ModelArtifact:
    path: str
    size: int
    digest: str
    digest_algorithm: str
    selected_by: str
    source: SourceLocation

    def to_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size": self.size,
            "digest": self.digest,
            "digest_algorithm": self.digest_algorithm,
            "selected_by": self.selected_by,
            "source": self.source.to_json(),
        }
