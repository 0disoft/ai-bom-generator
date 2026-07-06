from __future__ import annotations

import argparse
import configparser
import io
from pathlib import Path
import sys
import zipfile


REQUIRED_WHEEL_FILES = {
    "ai_bom_generator/exporters/cyclonedx_json/schema/bom-1.7.schema.json",
    "ai_bom_generator/exporters/cyclonedx_json/schema/LICENSE",
    "ai_bom_generator/exporters/cyclonedx_json/schema/__init__.py",
}

ENTRY_POINT_GROUP = "console_scripts"
ENTRY_POINT_NAME = "ai-bom"
ENTRY_POINT_TARGET = "ai_bom_generator.cli:main"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify AI-BOM Generator wheel contents.")
    parser.add_argument("dist_dir", type=Path, help="Directory containing exactly one built wheel.")
    args = parser.parse_args(argv)

    wheels = sorted(args.dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        print(f"expected exactly one wheel in {args.dist_dir}, found {len(wheels)}", file=sys.stderr)
        return 1

    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_WHEEL_FILES - names)
        if missing:
            print(f"wheel {wheel.name} is missing required files: {', '.join(missing)}", file=sys.stderr)
            return 1

        entry_points = _read_entry_points(archive)
        actual_target = entry_points.get(ENTRY_POINT_GROUP, ENTRY_POINT_NAME, fallback=None)
        if actual_target != ENTRY_POINT_TARGET:
            print(
                f"wheel {wheel.name} is missing console script entry point: "
                f"{ENTRY_POINT_NAME} = {ENTRY_POINT_TARGET}",
                file=sys.stderr,
            )
            return 1

    return 0


def _read_entry_points(archive: zipfile.ZipFile) -> configparser.ConfigParser:
    matches = [name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one entry_points.txt, found {len(matches)}")
    parser = configparser.ConfigParser()
    parser.read_file(io.StringIO(archive.read(matches[0]).decode("utf-8")))
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
