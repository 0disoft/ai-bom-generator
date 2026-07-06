from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from ai_bom_generator.errors import InvalidInputError
from ai_bom_generator.security.path_policy import PathPolicy


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
        with resolved.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise InvalidInputError(f"Invalid TOML config at {config_path}: {exc}", "config") from exc
    except OSError as exc:
        raise InvalidInputError(f"Cannot read config at {config_path}: {exc}", "config") from exc

    if not isinstance(data, dict):
        raise InvalidInputError("Config root must be a table.", "config")
    return LoadedConfig(path=resolved, data=data)
