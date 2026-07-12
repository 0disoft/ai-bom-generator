from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import tomllib
from typing import Any

from ai_bom_generator.errors import InvalidInputError
from ai_bom_generator.security.file_io import open_binary_nofollow
from ai_bom_generator.security.path_policy import PathPolicy
from ai_bom_generator.validation import SchemaValidationError, validate_with_schema


CONFIG_SCHEMA_PACKAGE = "ai_bom_generator.config.schema"
CONFIG_SCHEMA_NAME = "aibom-config-v1.schema.json"
DISCOVERED_CONFIG_NAME = "aibom.toml"


@dataclass(frozen=True)
class LoadedConfig:
    path: Path | None
    data: dict[str, Any]

    def get_table(self, name: str) -> dict[str, Any]:
        value = self.data.get(name, {})
        if isinstance(value, dict):
            return value
        raise InvalidInputError(f"Config section [{name}] must be a table.", "config")

    def get_array(self, name: str) -> list[dict[str, Any]]:
        value = self.data.get(name, [])
        if value is None:
            return []
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise InvalidInputError(f"Config section [[{name}]] must be an array of tables.", "config")
        return value


def load_config(config_path: Path | None, policy: PathPolicy) -> LoadedConfig:
    if config_path is None:
        config_path = _discover_config_path(policy)
        if config_path is None:
            return LoadedConfig(path=None, data={})

    raw = config_path if config_path.is_absolute() else Path.cwd() / config_path
    if raw.is_symlink():
        raise InvalidInputError(f"Symlink config is not allowed by default: {config_path}", "config")
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError as exc:
        raise InvalidInputError(f"Config file does not exist: {config_path}", "config") from exc
    policy.ensure_inside_root(resolved)
    if not resolved.is_file():
        raise InvalidInputError(f"Config path is not a file: {config_path}", "config")
    try:
        with open_binary_nofollow(resolved) as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise InvalidInputError(f"Invalid TOML config at {config_path}: {exc}", "config") from exc
    except OSError as exc:
        raise InvalidInputError(f"Cannot read config at {config_path}: {exc}", "config") from exc

    if not isinstance(data, dict):
        raise InvalidInputError("Config root must be a table.", "config")
    _validate_schema_version(data)
    _validate_config_schema(data)
    return LoadedConfig(path=resolved, data=data)


def _discover_config_path(policy: PathPolicy) -> Path | None:
    candidate = policy.root / DISCOVERED_CONFIG_NAME
    if not candidate.exists() and not candidate.is_symlink():
        return None
    return candidate


def _validate_schema_version(data: dict[str, Any]) -> None:
    schema_version = data.get("schema_version")
    if schema_version is None:
        raise InvalidInputError("Config schema_version is required.", "config")
    if schema_version != "1":
        raise InvalidInputError("Config schema_version must be \"1\".", "config")


def _validate_config_schema(data: dict[str, Any]) -> None:
    schema = resources.files(CONFIG_SCHEMA_PACKAGE).joinpath(CONFIG_SCHEMA_NAME)
    try:
        with resources.as_file(schema) as schema_path:
            validate_with_schema(data, schema_path, "AI-BOM config v1")
    except SchemaValidationError as exc:
        raise InvalidInputError(str(exc), "config") from exc
