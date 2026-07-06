from __future__ import annotations

from importlib import resources
from typing import Any

from ai_bom_generator.errors import ExporterError
from ai_bom_generator.validation import SchemaValidationError
from ai_bom_generator.validation.json_schema import validate_with_draft7


def validate_cyclonedx_1_7(payload: dict[str, Any]) -> None:
    schema_ref = resources.files("ai_bom_generator.exporters.cyclonedx_json.schema").joinpath("bom-1.7.schema.json")
    try:
        with resources.as_file(schema_ref) as schema_path:
            validate_with_draft7(payload, schema_path, "CycloneDX 1.7")
    except SchemaValidationError as exc:
        raise ExporterError(str(exc), "exporter-schema") from exc
