"""Explicit document authorship, separate from model provenance."""
from dataclasses import dataclass
from datetime import datetime, timezone
import re

from ai_bom_generator.errors import InvalidInputError


@dataclass(frozen=True)
class DocumentMetadata:
    created: str
    creator_name: str
    creator_type: str


def document_metadata(table: dict, created_override: str | None = None) -> DocumentMetadata:
    created = created_override if created_override is not None else table.get("created")
    name = table.get("creator_name")
    kind = table.get("creator_type")
    if not isinstance(name, str) or not name.strip() or len(name) > 256 or kind not in ("Person", "Organization"):
        raise InvalidInputError(
            'spdx-json-3.0.1 requires [spdx].creator_name and creator_type = "Person" or "Organization".',
            "config",
        )
    if not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", created):
        raise InvalidInputError(
            'Set [spdx].created or --document-created to an explicit timestamp, e.g. "2026-01-01T00:00:00Z".',
            "config",
        )
    try:
        parsed = datetime.fromisoformat(created)
        # Reject offsets outside the ISO timezone range even if datetime normalizes them.
        if not created.endswith("Z") and (int(created[-5:-3]) > 23 or int(created[-2:]) > 59):
            raise ValueError("invalid offset")
        normalized = parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError) as exc:
        raise InvalidInputError("Document creation timestamp is not a valid calendar date and timezone.", "config") from exc
    return DocumentMetadata(normalized, name.strip(), kind)
