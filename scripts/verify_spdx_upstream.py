"""Bounded, public-fixture-only upstream SPDX JSON Schema and SHACL gate."""
from __future__ import annotations

import copy
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from ai_bom_generator.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[1]


def validate(path: Path, *, expected: bool, diagnostic: str = "") -> None:
    executable = shutil.which("spdx3-validate")
    if not executable:
        raise RuntimeError("Install the declared upstream validation dependency first")
    result = subprocess.run([executable, "--quiet", "--json", str(path)], text=True,
                            capture_output=True, timeout=90)
    output = result.stdout + result.stderr
    if expected:
        if result.returncode != 0:
            raise RuntimeError(f"Positive upstream fixture failed: {path.name}\n{output[-5000:]}")
    elif result.returncode != 1 or diagnostic not in output:
        raise RuntimeError(f"Expected attributed mapping rejection: {path.name}\n{output[-5000:]}")
    print(json.dumps({"case": path.name, "expected_valid": expected, "passed": True}))


def main() -> None:
    print(json.dumps({"validator": "spdx3-validate", "version": version("spdx3-validate"),
                      "profile": "SPDX 3.0.1 Core/Software/AI", "exporter_conformance": "partial"}))
    with tempfile.TemporaryDirectory(prefix="aibom-spdx-gate-") as directory:
        work = Path(directory)
        for name in ("minimal", "complete"):
            source = ROOT / "tests/fixtures/spdx-upstream" / f"{name}.json"
            document = json.loads(source.read_text(encoding="utf-8"))
            validate(source, expected=True)
            roundtrip = work / f"{name}-roundtrip.json"
            roundtrip.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            validate(roundtrip, expected=True)
            invalid = copy.deepcopy(document)
            next(item for item in invalid["@graph"] if item["type"] == "CreationInfo").pop("created")
            broken = work / f"{name}-missing-created.json"
            broken.write_text(json.dumps(invalid), encoding="utf-8")
            validate(broken, expected=False, diagnostic="created")

            output = work / f"{name}-preview.json"
            project = "sparse-project" if name == "minimal" else "complete-project"
            code = cli_main(["generate", str(ROOT / "tests/fixtures" / project),
                             "--format", "spdx-ai", "--output", str(output),
                             "--warning-report", str(work / f"{name}-warnings.json"),
                             "--summary", str(work / f"{name}-summary.json")])
            if code != 0:
                raise RuntimeError(f"Local preview fixture failed: {name}: {code}")
            preview = json.loads(output.read_text(encoding="utf-8"))
            if preview.get("aiBom:conformance") != "partial":
                raise RuntimeError("Preview conformance marker changed without gate promotion")
            validate(output, expected=False, diagnostic="created")


if __name__ == "__main__":
    main()
