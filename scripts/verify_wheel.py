from __future__ import annotations

import argparse
import configparser
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


REQUIRED_WHEEL_FILES = {
    "ai_bom_generator/config/schema/aibom-config-v1.schema.json",
    "ai_bom_generator/exporters/cyclonedx_json/schema/bom-1.7.schema.json",
    "ai_bom_generator/exporters/cyclonedx_json/schema/LICENSE",
    "ai_bom_generator/exporters/cyclonedx_json/schema/__init__.py",
}

ENTRY_POINT_GROUP = "console_scripts"
ENTRY_POINT_NAME = "ai-bom"
ENTRY_POINT_TARGET = "ai_bom_generator.cli:main"
ROOT = Path(__file__).resolve().parents[1]


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

    return _verify_installed_entry_point(wheel)


def _verify_installed_entry_point(wheel: Path) -> int:
    with tempfile.TemporaryDirectory() as temp:
        venv = Path(temp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        python = _venv_python(venv)
        console = _venv_console(venv)

        install = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(wheel),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if install.returncode != 0:
            print(install.stdout, file=sys.stderr)
            print(install.stderr, file=sys.stderr)
            print(f"failed to install wheel {wheel.name} into isolated venv", file=sys.stderr)
            return install.returncode

        env = _runtime_env_with_locked_dependencies()
        source_check = subprocess.run(
            [
                str(python),
                "-c",
                "from pathlib import Path; import ai_bom_generator; print(Path(ai_bom_generator.__file__).resolve())",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if source_check.returncode != 0:
            print(source_check.stderr, file=sys.stderr)
            return source_check.returncode
        imported_from = Path(source_check.stdout.strip())
        if _is_relative_to(imported_from, ROOT / "src"):
            print(f"installed wheel imported package from source tree: {imported_from}", file=sys.stderr)
            return 1

        help_check = subprocess.run(
            [str(console), "--help"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if help_check.returncode != 0 or "generate" not in help_check.stdout:
            print(help_check.stdout, file=sys.stderr)
            print(help_check.stderr, file=sys.stderr)
            print("installed ai-bom console script did not render help", file=sys.stderr)
            return help_check.returncode or 1

        metadata_check = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata; print(importlib.metadata.version('ai-bom-generator'))",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if metadata_check.returncode != 0:
            print(metadata_check.stdout, file=sys.stderr)
            print(metadata_check.stderr, file=sys.stderr)
            print("installed wheel version metadata could not be read", file=sys.stderr)
            return metadata_check.returncode

        expected_version_output = f"ai-bom-generator {metadata_check.stdout.strip()}\n"
        version_check = subprocess.run(
            [str(console), "--version"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if (
            version_check.returncode != 0
            or version_check.stdout != expected_version_output
            or version_check.stderr
        ):
            print(version_check.stdout, file=sys.stderr)
            print(version_check.stderr, file=sys.stderr)
            print("installed ai-bom console script did not render package version", file=sys.stderr)
            return version_check.returncode or 1

        out = Path(temp) / "out"
        out.mkdir()
        smoke = subprocess.run(
            [
                str(console),
                "generate",
                str(ROOT / "tests" / "fixtures" / "complete-project"),
                "--format",
                "cyclonedx-json-1.7",
                "--output",
                str(out / "bom.cdx.json"),
                "--warning-report",
                str(out / "warnings.json"),
                "--summary",
                str(out / "summary.json"),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if smoke.returncode != 0:
            print(smoke.stdout, file=sys.stderr)
            print(smoke.stderr, file=sys.stderr)
            print("installed ai-bom console script smoke failed", file=sys.stderr)
            return smoke.returncode
        for path in (out / "bom.cdx.json", out / "warnings.json", out / "summary.json"):
            if not path.is_file() or path.stat().st_size == 0:
                print(f"installed ai-bom smoke did not create non-empty output: {path}", file=sys.stderr)
                return 1

    return 0


def _read_entry_points(archive: zipfile.ZipFile) -> configparser.ConfigParser:
    matches = [name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one entry_points.txt, found {len(matches)}")
    parser = configparser.ConfigParser()
    parser.read_file(io.StringIO(archive.read(matches[0]).decode("utf-8")))
    return parser


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _venv_console(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "ai-bom.exe"
    return venv / "bin" / "ai-bom"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _runtime_env_with_locked_dependencies() -> dict[str, str]:
    env = os.environ.copy()
    dependency_roots = _locked_dependency_roots()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join([*map(str, dependency_roots), existing] if existing else map(str, dependency_roots))
    return env


def _locked_dependency_roots() -> list[Path]:
    roots: set[Path] = set()
    for module_name in ("attrs", "jsonschema", "jsonschema_specifications", "referencing", "rpds"):
        module = importlib.import_module(module_name)
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        root = Path(module_file).resolve().parent.parent
        if _is_relative_to(root, ROOT / "src"):
            continue
        roots.add(root)
    return sorted(roots)


if __name__ == "__main__":
    raise SystemExit(main())
