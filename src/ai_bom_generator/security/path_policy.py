from __future__ import annotations

from pathlib import Path

from ai_bom_generator.errors import InvalidInputError


class PathPolicy:
    def __init__(self, target_root: Path) -> None:
        self.root = target_root.resolve(strict=True)
        if not self.root.is_dir():
            raise InvalidInputError(f"Target model directory is not a directory: {target_root}", "input")

    def resolve_existing_file(self, candidate: Path | str, required: bool) -> Path:
        raw = Path(candidate)
        path = raw if raw.is_absolute() else self.root / raw
        if path.is_symlink():
            raise InvalidInputError(f"Symlink file is not allowed by default: {candidate}", "input")
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError as exc:
            qualifier = "Required" if required else "Referenced"
            raise InvalidInputError(f"{qualifier} file does not exist: {candidate}", "input") from exc

        self.ensure_inside_root(resolved)
        if not resolved.is_file():
            raise InvalidInputError(f"Expected a file: {candidate}", "input")
        return resolved

    def resolve_output_file(self, candidate: Path | str) -> Path:
        raw = Path(candidate)
        path = raw if raw.is_absolute() else Path.cwd() / raw
        return path.resolve(strict=False)

    def ensure_inside_root(self, resolved: Path) -> None:
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise InvalidInputError(f"Path escapes target root: {resolved}", "input") from exc

    def relative_to_root(self, resolved: Path) -> str:
        self.ensure_inside_root(resolved)
        return resolved.relative_to(self.root).as_posix()
