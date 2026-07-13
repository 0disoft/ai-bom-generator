from __future__ import annotations

from ai_bom_generator import __version__
from ai_bom_generator.errors import AIBomError, ExitCode
from ai_bom_generator.security import Redactor


_ERROR_CODES = {
    ExitCode.INVALID_INPUT: "INVALID_INPUT",
    ExitCode.COLLECTOR_FAILURE: "COLLECTOR_FAILURE",
    ExitCode.EXPORTER_FAILURE: "EXPORTER_FAILURE",
    ExitCode.INTERNAL_ERROR: "INTERNAL_ERROR",
}


def build_error_report(error: AIBomError | Exception, redactor: Redactor) -> dict[str, object]:
    if isinstance(error, AIBomError):
        exit_code = error.exit_code
        stage = error.stage
        message = error.message
    else:
        exit_code = ExitCode.INTERNAL_ERROR
        stage = "internal-error"
        message = str(error) or "Unexpected internal failure."

    payload: dict[str, object] = {
        "schema_version": "ai-bom-error-report/v1",
        "tool": {
            "name": "ai-bom-generator",
            "version": __version__,
        },
        "status": "failed",
        "error": {
            "code": _ERROR_CODES.get(exit_code, "INTERNAL_ERROR"),
            "stage": stage,
            "message": message,
        },
        "exit_code": exit_code,
    }
    redacted = redactor.redact_json(payload)
    if not isinstance(redacted, dict):
        raise TypeError("Error report redaction returned an invalid JSON object.")
    return redacted
