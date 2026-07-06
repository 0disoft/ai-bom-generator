from __future__ import annotations

from dataclasses import dataclass

from ai_bom_generator.domain.source_location import SourceLocation


@dataclass(frozen=True, order=True)
class Warning:
    code: str
    severity: str
    object_kind: str
    object_id: str
    message: str
    source: SourceLocation | None = None
    remediation: str | None = None

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "message": self.message,
        }
        if self.source:
            data["source"] = self.source.to_json()
        if self.remediation:
            data["remediation"] = self.remediation
        return data
