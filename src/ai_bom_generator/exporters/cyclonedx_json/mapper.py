from __future__ import annotations

from hashlib import sha256

from ai_bom_generator.domain.dependency import DependencyPackage
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.errors import ExporterError
from ai_bom_generator.exporters.cyclonedx_schema import validate_cyclonedx_1_7
from ai_bom_generator.security import Redactor


SUPPORTED_FORMAT = "cyclonedx-json-1.7"


def export_cyclonedx_json(evidence: NormalizedEvidence, redactor: Redactor) -> dict[str, object]:
    components: list[dict[str, object]] = []
    for artifact in evidence.artifacts:
        components.append(
            {
                "type": "file",
                "name": artifact.path,
                "bom-ref": f"artifact:{artifact.path}",
                "hashes": [{"alg": "SHA-256", "content": artifact.digest}],
                "properties": [
                    {"name": "ai-bom:selected-by", "value": artifact.selected_by},
                    {"name": "ai-bom:size", "value": str(artifact.size)},
                ],
            }
        )

    for reference in [*evidence.dependencies, *evidence.datasets, *evidence.prompts, *evidence.evals, *evidence.training]:
        components.append(
            {
                "type": "data",
                "name": reference.object_id,
                "bom-ref": f"{reference.kind}:{reference.object_id}",
                "properties": [
                    {"name": f"ai-bom:{key}", "value": value}
                    for key, value in sorted(reference.values)
                ],
            }
        )

    for package in evidence.dependency_packages:
        component: dict[str, object] = {
            "type": "library",
            "name": package.name,
            "bom-ref": _dependency_package_ref(package.identity_key()),
            "properties": _dependency_package_properties(package),
        }
        if package.version:
            component["version"] = package.version
        components.append(component)

    model_name = evidence.model_metadata[0].object_id if evidence.model_metadata else "unnamed-model"
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "component": {
                "type": "machine-learning-model",
                "name": model_name,
                "properties": _model_properties(evidence),
            }
        },
        "components": sorted(components, key=lambda item: str(item.get("bom-ref", ""))),
    }
    redacted = redactor.redact_json(bom)
    if not isinstance(redacted, dict):
        raise ExporterError("CycloneDX exporter produced a non-object BOM.", "exporter")
    _validate_unique_bom_refs(redacted)
    validate_cyclonedx_1_7(redacted)
    return redacted


def _dependency_package_ref(identity_key: str) -> str:
    digest = sha256(identity_key.encode("utf-8")).hexdigest()[:24]
    return f"dependency-package:{digest}"


def _dependency_package_properties(package: DependencyPackage) -> list[dict[str, str]]:
    properties = [
        {"name": "ai-bom:dependency:lockfile-format", "value": package.lockfile_format},
        {"name": "ai-bom:dependency:requirement", "value": package.requirement},
        {"name": "ai-bom:dependency:source-path", "value": package.source.path},
        {"name": "ai-bom:dependency:source-type", "value": package.source_type},
    ]
    if package.marker:
        properties.append({"name": "ai-bom:dependency:marker", "value": package.marker})
    if package.source_locator:
        properties.append({"name": "ai-bom:dependency:source-locator", "value": package.source_locator})
    if package.package_source.channel:
        properties.append({"name": "ai-bom:dependency:source-channel", "value": package.package_source.channel})
    if package.package_source.index:
        properties.append({"name": "ai-bom:dependency:source-index", "value": package.package_source.index})
    if package.package_source.platform:
        properties.append({"name": "ai-bom:dependency:source-platform", "value": package.package_source.platform})
    if package.package_source.revision:
        properties.append({"name": "ai-bom:dependency:source-revision", "value": package.package_source.revision})
    for index, artifact_hash in enumerate(package.package_source.artifact_hashes):
        prefix = f"ai-bom:dependency:artifact:{index}"
        properties.append(
            {
                "name": f"{prefix}:hash",
                "value": f"{artifact_hash.algorithm}:{artifact_hash.value}",
            }
        )
        if artifact_hash.locator:
            properties.append({"name": f"{prefix}:locator", "value": artifact_hash.locator})
    if package.extras:
        properties.append({"name": "ai-bom:dependency:extras", "value": ",".join(package.extras)})
    return sorted(properties, key=lambda item: item["name"])


def _model_properties(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    properties: list[dict[str, str]] = [
        {"name": "ai-bom:completeness-status", "value": evidence.completeness_status},
        {"name": "ai-bom:warning-count", "value": str(evidence.warning_count)},
    ]
    if evidence.generation_marker:
        properties.extend(
            [
                {"name": "ai-bom:generation-marker:path", "value": evidence.generation_marker.path},
                {
                    "name": "ai-bom:generation-marker:sha-256",
                    "value": evidence.generation_marker.digest,
                },
            ]
        )
    for reference in evidence.model_metadata:
        for key, value in reference.values:
            properties.append({"name": f"ai-bom:model:{key}", "value": value})
    for reference in evidence.git:
        for key, value in reference.values:
            properties.append({"name": f"ai-bom:git:{key}", "value": value})
    return sorted(properties, key=lambda item: item["name"])


def _validate_unique_bom_refs(bom: dict[str, object]) -> None:
    components = bom.get("components", [])
    if not isinstance(components, list):
        return

    seen: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            continue
        bom_ref = component.get("bom-ref")
        if not isinstance(bom_ref, str):
            continue
        if bom_ref in seen:
            raise ExporterError(f"CycloneDX exporter produced duplicate bom-ref: {bom_ref}", "exporter")
        seen.add(bom_ref)
