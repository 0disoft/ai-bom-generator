from dataclasses import replace

from ai_bom_generator.config.loader import LoadedConfig
from ai_bom_generator.errors import InvalidInputError


LIMIT_CEILINGS = {
    "matches_per_pattern": 256,
    "single_file_bytes": 16 * 1024**3,
    "total_bytes": 25 * 1024**3,
    "visited_entries": 100_000,
}


def apply_artifact_overrides(config: LoadedConfig, discovery: bool | None, overrides: dict[str, int | None]) -> LoadedConfig:
    artifacts = dict(config.get_table("artifacts"))
    limits = dict(artifacts.get("limits", {}))
    limits.update({name: value for name, value in overrides.items() if value is not None})
    for name, value in limits.items():
        ceiling = LIMIT_CEILINGS.get(name)
        if ceiling is None or type(value) is not int or not 1 <= value <= ceiling:
            raise InvalidInputError(f"Artifact limit {name} must be an integer from 1 through {ceiling}.", "config")
    if discovery is not None:
        artifacts["discovery"] = discovery
    if limits:
        artifacts["limits"] = limits
    return replace(config, data={**config.data, "artifacts": artifacts})
