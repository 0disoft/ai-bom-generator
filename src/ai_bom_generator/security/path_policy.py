from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

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

    def validate_output_file(self, candidate: Path | str, label: str) -> Path:
        raw = Path(candidate)
        path = raw if raw.is_absolute() else Path.cwd() / raw
        if path.exists() and path.is_symlink():
            raise InvalidInputError(f"{label} output path must not be a symlink: {candidate}", "input")
        resolved = path.resolve(strict=False)
        if self.is_inside_root(resolved):
            raise InvalidInputError(f"{label} output path must be outside target model directory: {candidate}", "input")
        return resolved

    def validate_relative_glob(self, pattern: str, label: str) -> str:
        if not pattern:
            raise InvalidInputError(f"{label} glob pattern must not be empty.", "config")
        posix = PurePosixPath(pattern)
        windows = PureWindowsPath(pattern)
        if posix.is_absolute() or windows.is_absolute() or posix.anchor or windows.drive or windows.root:
            raise InvalidInputError(f"{label} glob pattern must be relative to the target root: {pattern}", "config")
        if ".." in posix.parts or ".." in windows.parts:
            raise InvalidInputError(f"{label} glob pattern must not contain parent traversal: {pattern}", "config")
        return pattern

    def ensure_inside_root(self, resolved: Path) -> None:
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise InvalidInputError(f"Path escapes target root: {resolved}", "input") from exc

    def is_inside_root(self, resolved: Path) -> bool:
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return False
        return True

    def relative_to_root(self, resolved: Path) -> str:
        self.ensure_inside_root(resolved)
        return resolved.relative_to(self.root).as_posix()
