"""Bounded, public-fixture-only upstream SPDX JSON Schema and SHACL gate."""
from __future__ import annotations

import copy
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
import shutil
import spdx_python_model

from ai_bom_generator.cli import main as cli_main
try:
    from .spdx_validation_resources import RESOURCES, UpstreamValidator
except ImportError:
    from spdx_validation_resources import RESOURCES, UpstreamValidator


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = None


def consume(path: Path) -> None:
    """Read actual CLI output through the independent SPDX object model."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    model, objects = spdx_python_model.load(path)
    for item in raw["@graph"]:
        identifier = item.get("spdxId", item.get("@id"))
        if item["type"] == "CreationInfo":
            # The reader resolves blank nodes but does not index their source IDs.
            candidates = list(objects.foreach_type("CreationInfo"))
            if len(candidates) != 1:
                raise RuntimeError("Consumer did not recover one CreationInfo")
            obj = candidates[0]
        else:
            obj = objects.obj_by_id[identifier]
        if not isinstance(obj, getattr(model, item["type"])):
            raise RuntimeError(f"Consumer lost element type: {item['type']}")
        for field in ("name", "comment", "software_packageVersion"):
            if field in item and getattr(obj, field) != item[field]:
                raise RuntimeError(f"Consumer changed evidence field: {field}")
        if item["type"] == "Relationship":
            if obj.from_.spdxId != item["from"]:
                raise RuntimeError("Consumer did not resolve relationship source")
            if {target.spdxId for target in obj.to} != set(item["to"]):
                raise RuntimeError("Consumer did not resolve relationship targets")
            if obj.relationshipType.rsplit("/", 1)[-1] != item["relationshipType"]:
                raise RuntimeError("Consumer changed relationship type")
        if item["type"] == "SpdxDocument":
            if {root.spdxId for root in obj.rootElement} != set(item["rootElement"]):
                raise RuntimeError("Consumer did not resolve document roots")
            if obj.creationInfo.specVersion != "3.0.1":
                raise RuntimeError("Consumer selected wrong SPDX version")
            if obj.creationInfo.createdBy[0].name != "Synthetic producer":
                raise RuntimeError("Consumer lost explicitly declared author")
    print(json.dumps({"case": path.name, "consumer": "spdx-python-model",
                      "version": version("spdx-python-model"), "passed": True}))


def validate(path: Path, *, expected: bool, diagnostic: str = "") -> None:
    if VALIDATOR is None:
        raise RuntimeError("Initialize the verified upstream resources first")
    errors = VALIDATOR.errors(path)
    output = "\n".join(errors)
    if expected:
        if errors:
            raise RuntimeError(f"Positive upstream fixture failed: {path.name}\n{output[-5000:]}")
    elif not errors or diagnostic not in output:
        raise RuntimeError(f"Expected attributed mapping rejection: {path.name}\n{output[-5000:]}")
    print(json.dumps({"case": path.name, "expected_valid": expected, "passed": True}))


def main() -> None:
    global VALIDATOR
    print(json.dumps({"validator": "spdx3-validate", "version": version("spdx3-validate"),
                      "profile": "SPDX 3.0.1 Core/Software/AI", "exporter_conformance": "partial"}))
    print(json.dumps({"resources": RESOURCES, "cache": "verified in-memory, one fetch per resource per run"}))
    VALIDATOR = UpstreamValidator()
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

            compatible_project = work / f"{name}-project"
            shutil.copytree(ROOT / "tests/fixtures" / project, compatible_project)
            config_path = compatible_project / "aibom.toml"
            original = config_path.read_text(encoding="utf-8") if config_path.exists() else 'schema_version = "1"\n'
            config_path.write_text(original + '\n[spdx]\ncreator_name = "Synthetic producer"\n'
                                   'creator_type = "Organization"\ncreated = "2026-01-01T00:00:00Z"\n', encoding="utf-8")
            compatible = work / f"{name}-compatible.json"
            code = cli_main(["generate", str(compatible_project), "--format", "spdx-json-3.0.1",
                             "--output", str(compatible), "--warning-report", str(work / f"{name}-compatible-warnings.json"),
                             "--summary", str(work / f"{name}-compatible-summary.json")])
            if code != 0:
                raise RuntimeError(f"Compatible CLI fixture failed: {name}: {code}")
            validate(compatible, expected=True)
            consume(compatible)
            broken_document = json.loads(compatible.read_text(encoding="utf-8"))
            next(item for item in broken_document["@graph"] if item["type"] == "CreationInfo").pop("createdBy")
            invalid_creator = work / f"{name}-compatible-missing-creator.json"
            invalid_creator.write_text(json.dumps(broken_document), encoding="utf-8")
            validate(invalid_creator, expected=False, diagnostic="createdBy")
            relationships = [item for item in broken_document["@graph"] if item["type"] == "Relationship"]
            if relationships:
                broken_document = json.loads(compatible.read_text(encoding="utf-8"))
                next(item for item in broken_document["@graph"] if item["type"] == "Relationship").pop("from")
                invalid_relation = work / f"{name}-compatible-missing-from.json"
                invalid_relation.write_text(json.dumps(broken_document), encoding="utf-8")
                validate(invalid_relation, expected=False, diagnostic="from")


if __name__ == "__main__":
    main()
