from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.source_location import SourceLocation


@dataclass(frozen=True, order=True)
class DeclaredReference:
    kind: str
    object_id: str
    values: tuple[tuple[str, str], ...]
    source: SourceLocation

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "object_id": self.object_id,
            "values": dict(self.values),
            "source": self.source.to_json(),
        }
