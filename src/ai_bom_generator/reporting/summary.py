from __future__ import annotations

from pathlib import Path

from ai_bom_generator import __version__
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.errors import ExitCode, ExporterError
from ai_bom_generator.security import Redactor


def build_summary(
    evidence: NormalizedEvidence,
    bom_path: Path,
    warning_report_path: Path,
    output_format: str,
    elapsed_ms: int,
    warning_policy_failed: bool,
    redactor: Redactor,
) -> dict[str, object]:
    status = "success"
    if warning_policy_failed:
        status = "failed"
    elif evidence.warning_count:
        status = "success-with-warnings"

    payload = {
        "schema_version": "1",
        "tool": {"name": "ai-bom-generator", "version": __version__},
        "status": status,
        "format": output_format,
        "bom_path": bom_path.as_posix(),
        "warning_report_path": warning_report_path.as_posix(),
        "hash_algorithm": "sha256",
        "artifact_count": len(evidence.artifacts),
        "warning_count": evidence.warning_count,
        "completeness_status": evidence.completeness_status,
        "warnings": [warning.to_json() for warning in evidence.warnings],
        "elapsed_ms": elapsed_ms,
        "exit_code": ExitCode.WARNING_POLICY_FAILED if warning_policy_failed else ExitCode.SUCCESS,
    }
    redacted = redactor.redact_json(payload)
    if not isinstance(redacted, dict):
        raise ExporterError("Summary redaction returned an invalid JSON object.", "summary")
    return redacted
