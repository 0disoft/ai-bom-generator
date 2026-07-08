from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@"),
    re.compile(r"(?i)([?&](?:token|access_token|api_key|key|secret|password|credential|authorization)=)[^&\s]+"),
    re.compile(r"(?i)\b((?:token|access_token|api_key|key|secret|password|credential|authorization)=)[^&\s]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)\b(?:ghp|gho|github_pat|sk|sk-proj)-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bya29\.[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bxox(?:a|b|p|r)-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]

_SENSITIVE_KEY_NAMES = {
    "access_key",
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "credential",
    "credentials",
    "identity_token",
    "id_token",
    "key",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}


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

    def redact_key_value(self, key: str, value: Any) -> Any:
        if self.mode == "off":
            return value
        if _is_sensitive_key(key):
            return "REDACTED"
        return self.redact_json(value)

    def redact_json(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, list):
            return [self.redact_json(item) for item in value]
        if isinstance(value, tuple):
            return [self.redact_json(item) for item in value]
        if isinstance(value, dict):
            return {key: self.redact_key_value(str(key), item) for key, item in value.items()}
        return value


def _mask_match(match: re.Match[str]) -> str:
    if match.lastindex:
        return match.group(1) + "REDACTED"
    return "REDACTED"


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    if normalized in _SENSITIVE_KEY_NAMES:
        return True
    parts = [part for part in normalized.split("_") if part]
    if not parts:
        return False
    if parts[-1] in {"token", "secret", "password", "credential", "credentials"}:
        return True
    return normalized.endswith("_api_key") or normalized.endswith("_access_key") or normalized.endswith("_private_key")
