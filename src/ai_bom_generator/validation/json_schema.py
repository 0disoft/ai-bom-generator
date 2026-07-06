from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, validators


@dataclass(frozen=True)
class SchemaValidationError(Exception):
    schema_name: str
    message: str
    path: tuple[str, ...]

    def __str__(self) -> str:
        location = ".".join(self.path) if self.path else "<root>"
        return f"{self.schema_name} validation failed at {location}: {self.message}"


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_with_schema(payload: Any, schema_path: Path, schema_name: str) -> None:
    schema = load_schema(schema_path)
    validator_class = validators.validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        raise SchemaValidationError(schema_name=schema_name, message=first.message, path=tuple(str(item) for item in first.path))


def validate_with_draft7(payload: Any, schema_path: Path, schema_name: str) -> None:
    schema = load_schema(schema_path)
    Draft7Validator.check_schema(schema)
    errors = sorted(Draft7Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        raise SchemaValidationError(schema_name=schema_name, message=first.message, path=tuple(str(item) for item in first.path))
