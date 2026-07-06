from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@"),
    re.compile(r"(?i)([?&](?:token|access_token|api_key|key|secret)=)[^&\s]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)\b(?:ghp|gho|github_pat|sk|sk-proj)-[A-Za-z0-9_\-]{12,}\b"),
]


class Redactor:
    def __init__(self, mode: str) -> None:
        if mode not in {"strict", "off"}:
            raise ValueError(f"Unsupported redaction mode: {mode}")
        self.mode = mode

    def redact_text(self, value: str) -> str:
        if self.mode == "off":
            return value
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(lambda match: _mask_match(match), redacted)
        return redacted

    def redact_json(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, list):
            return [self.redact_json(item) for item in value]
        if isinstance(value, tuple):
            return [self.redact_json(item) for item in value]
        if isinstance(value, dict):
            return {key: self.redact_json(item) for key, item in value.items()}
        return value


def _mask_match(match: re.Match[str]) -> str:
    if match.lastindex:
        return match.group(1) + "REDACTED"
    return "REDACTED"
