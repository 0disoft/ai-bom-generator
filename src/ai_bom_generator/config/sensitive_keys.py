from __future__ import annotations

from ai_bom_generator.config.loader import LoadedConfig
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.domain.warning import Warning
from ai_bom_generator.security.redaction import _is_sensitive_key


def sensitive_config_warnings(config: LoadedConfig) -> list[Warning]:
    """Report only schema-owned section/index locations, never caller keys or values."""
    warnings: list[Warning] = []
    for section in ("model", "dependencies", "datasets", "prompts", "evals", "training"):
        value = config.data.get(section)
        records = enumerate(value) if isinstance(value, list) else [(None, value)]
        for index, record in records:
            pending = [record]
            found = False
            while pending:
                current = pending.pop()
                if isinstance(current, dict):
                    if any(_is_sensitive_key(str(key)) for key in current):
                        found = True
                        break
                    pending.extend(current.values())
                elif isinstance(current, list):
                    pending.extend(current)
            if not found:
                continue
            location = section if index is None else f"{section}[{index}]"
            warnings.append(Warning(
                code="SENSITIVE_CONFIG_KEY",
                severity="warning",
                object_kind="config",
                object_id=location,
                message="A sensitive key was found in declared config metadata; remove credential-bearing fields.",
                source=SourceLocation(path="<config>", field=location, collector="config"),
                remediation="Keep credentials outside evidence configuration. Redaction is best effort.",
            ))
    return warnings
