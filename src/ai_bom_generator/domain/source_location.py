from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class SourceLocation:
    path: str
    field: str | None = None
    collector: str | None = None

    def to_json(self) -> dict[str, str]:
        data = {"path": self.path}
        if self.field:
            data["field"] = self.field
        if self.collector:
            data["collector"] = self.collector
        return data
