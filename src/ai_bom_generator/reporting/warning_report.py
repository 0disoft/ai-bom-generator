from __future__ import annotations

from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.errors import ExporterError
from ai_bom_generator.security import Redactor


def build_warning_report(evidence: NormalizedEvidence, redactor: Redactor) -> dict[str, object]:
    payload = {
        "schema_version": "1",
        "warning_count": evidence.warning_count,
        "warnings": [warning.to_json() for warning in evidence.warnings],
    }
    redacted = redactor.redact_json(payload)
    if not isinstance(redacted, dict):
        raise ExporterError("Warning report redaction returned an invalid JSON object.", "warning_report")
    return redacted
