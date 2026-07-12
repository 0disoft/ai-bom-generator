from __future__ import annotations

from hashlib import sha256
from importlib import resources

from ai_bom_generator import __version__
from ai_bom_generator.domain.dependency import DependencyPackage
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.domain.reference import DeclaredReference
from ai_bom_generator.errors import ExporterError
from ai_bom_generator.security import Redactor
from ai_bom_generator.validation import SchemaValidationError, validate_with_schema


SUPPORTED_FORMAT = "spdx-ai"
_SPDX_SPEC_VERSION = "3.0.1"
_SPDX_CONTEXT = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
_SPDX_CORE_PROFILE = "https://spdx.org/rdf/3.0.1/terms/Core"
_SPDX_SOFTWARE_PROFILE = "https://spdx.org/rdf/3.0.1/terms/Software"
_SPDX_AI_PROFILE = "https://spdx.org/rdf/3.0.1/terms/AI"
_SPDX_NO_ASSERTION = "https://spdx.org/rdf/3.0.1/terms/Core/NoAssertionElement"
_SPDX_NAMESPACE = "urn:ai-bom-generator:spdx-ai"
_LOCAL_SCHEMA = "aibom-spdx-ai-preview.schema.json"


def export_spdx_ai(evidence: NormalizedEvidence, redactor: Redactor) -> dict[str, object]:
    creation_info_id = f"{_SPDX_NAMESPACE}:creation-info"
    tool_id = f"{_SPDX_NAMESPACE}:tool"
    model_id = f"{_SPDX_NAMESPACE}:model"
    references = _all_declared_references(evidence)
    reference_elements = [_reference_element(reference, creation_info_id) for reference in references]
    dependency_package_elements = [
        _dependency_package_element(package, creation_info_id) for package in evidence.dependency_packages
    ]
    artifact_elements = [
        {
            "type": "software_File",
            "spdxId": _stable_spdx_id("artifact", artifact.path),
            "name": artifact.path,
            "creationInfo": creation_info_id,
            "verifiedUsing": [
                {
                    "algorithm": artifact.digest_algorithm.upper().replace("-", ""),
                    "hashValue": artifact.digest,
                }
            ],
            "aiBom:path": artifact.path,
            "aiBom:selectedBy": artifact.selected_by,
            "aiBom:sizeBytes": artifact.size,
        }
        for artifact in evidence.artifacts
    ]
    related_ids = sorted(
        [
            *[str(item["spdxId"]) for item in artifact_elements],
            *[str(item["spdxId"]) for item in dependency_package_elements],
            *[str(item["spdxId"]) for item in reference_elements],
        ]
    )

    graph: list[dict[str, object]] = [
        {
            "type": "SpdxDocument",
            "spdxId": f"{_SPDX_NAMESPACE}:document",
            "name": f"AI-BOM for {_model_name(evidence)}",
            "specVersion": _SPDX_SPEC_VERSION,
            "profileConformance": [_SPDX_CORE_PROFILE, _SPDX_SOFTWARE_PROFILE, _SPDX_AI_PROFILE],
            "creationInfo": creation_info_id,
            "rootElement": [model_id],
        },
        {
            "type": "CreationInfo",
            "spdxId": creation_info_id,
            "createdBy": [tool_id],
            "createdUsing": [tool_id],
        },
        {
            "type": "Tool",
            "spdxId": tool_id,
            "name": "ai-bom-generator",
            "packageVersion": __version__,
        },
        _model_package(evidence, creation_info_id, model_id),
        *artifact_elements,
        *dependency_package_elements,
        *reference_elements,
    ]
    if related_ids:
        graph.append(
            {
                "type": "Relationship",
                "spdxId": f"{_SPDX_NAMESPACE}:relationship:model-contains-evidence",
                "creationInfo": creation_info_id,
                "from": model_id,
                "relationshipType": "contains",
                "to": related_ids,
            }
        )

    payload = {
        "@context": _SPDX_CONTEXT,
        "@graph": sorted(graph, key=lambda item: str(item.get("spdxId", ""))),
        "aiBom:format": SUPPORTED_FORMAT,
        "aiBom:spdxTarget": "SPDX 3.0.1 AI Profile preview",
        "aiBom:conformance": "partial",
        "aiBom:contract": "docs/contracts/spdx-ai.md",
    }
    redacted = redactor.redact_json(payload)
    if not isinstance(redacted, dict):
        raise ExporterError("SPDX AI exporter produced a non-object BOM.", "exporter")
    _validate_unique_spdx_ids(redacted)
    _validate_spdx_ai_preview(redacted)
    return redacted


def _model_package(evidence: NormalizedEvidence, creation_info_id: str, model_id: str) -> dict[str, object]:
    values = _model_values(evidence)
    unavailable = _unavailable_spdx_ai_fields(values)
    package: dict[str, object] = {
        "type": "ai_AIPackage",
        "spdxId": model_id,
        "name": _model_name(evidence),
        "creationInfo": creation_info_id,
        "primaryPurpose": "machine-learning-model",
        "summary": "Local AI/ML model project evidence collected by ai-bom-generator.",
        "aiBom:completenessStatus": evidence.completeness_status,
        "aiBom:warningCount": evidence.warning_count,
        "aiBom:unavailableSpdxAiFields": unavailable,
        "aiBom:unsupportedSpdxAiFields": [
            "additionalPurpose",
            "energyConsumption",
            "hyperparameter",
            "metric",
            "safetyRiskAssessment",
            "sensitivePersonalInformation",
            "standardCompliance",
        ],
    }
    if version := values.get("version"):
        package["packageVersion"] = version
    else:
        package["packageVersion"] = "NOASSERTION"
    if license_declared := values.get("license_declared"):
        package["aiBom:licenseDeclared"] = license_declared
    if model_card := values.get("model_card"):
        package["aiBom:modelCard"] = model_card
    if supplied_by := _first_present(values, ("supplied_by", "supplier", "publisher")):
        package["suppliedBy"] = supplied_by
    if download_location := _first_present(values, ("download_location", "download_url", "uri")):
        package["downloadLocation"] = download_location
    if release_time := _first_present(values, ("release_time", "release_date")):
        package["aiBom:releaseTime"] = release_time
    return package


def _reference_element(reference: DeclaredReference, creation_info_id: str) -> dict[str, object]:
    values = dict(reference.values)
    element: dict[str, object] = {
        "type": "aiBom_Reference",
        "spdxId": _stable_spdx_id(reference.kind, reference.object_id),
        "name": reference.object_id,
        "creationInfo": creation_info_id,
        "aiBom:kind": reference.kind,
    }
    for key, value in sorted(values.items()):
        element[f"aiBom:{key}"] = value
    return element


def _dependency_package_element(
    package: DependencyPackage,
    creation_info_id: str,
) -> dict[str, object]:
    element: dict[str, object] = {
        "type": "software_Package",
        "spdxId": _stable_spdx_id("dependency-package", package.identity_key()),
        "name": package.name,
        "packageVersion": package.version or "NOASSERTION",
        "creationInfo": creation_info_id,
        "aiBom:lockfileFormat": package.lockfile_format,
        "aiBom:requirement": package.requirement,
        "aiBom:sourcePath": package.source.path,
        "aiBom:sourceType": package.source_type,
    }
    if package.marker:
        element["aiBom:marker"] = package.marker
    if package.extras:
        element["aiBom:extras"] = list(package.extras)
    return element


def _all_declared_references(evidence: NormalizedEvidence) -> list[DeclaredReference]:
    return sorted([*evidence.dependencies, *evidence.datasets, *evidence.prompts, *evidence.evals, *evidence.training, *evidence.git])


def _model_values(evidence: NormalizedEvidence) -> dict[str, str]:
    if not evidence.model_metadata:
        return {}
    return dict(evidence.model_metadata[0].values)


def _model_name(evidence: NormalizedEvidence) -> str:
    if evidence.model_metadata:
        return evidence.model_metadata[0].object_id
    return "unnamed-model"


def _first_present(values: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = values.get(key)
        if value:
            return value
    return None


def _unavailable_spdx_ai_fields(values: dict[str, str]) -> list[str]:
    unavailable: list[str] = []
    if not _first_present(values, ("supplied_by", "supplier", "publisher")):
        unavailable.append("suppliedBy")
    if not _first_present(values, ("download_location", "download_url", "uri")):
        unavailable.append("downloadLocation")
    if not _first_present(values, ("release_time", "release_date")):
        unavailable.append("releaseTime")
    return unavailable


def _stable_spdx_id(kind: str, object_id: str) -> str:
    digest = sha256(f"{kind}:{object_id}".encode("utf-8")).hexdigest()[:16]
    return f"{_SPDX_NAMESPACE}:{kind}:{digest}"


def _validate_unique_spdx_ids(payload: dict[str, object]) -> None:
    graph = payload.get("@graph", [])
    if not isinstance(graph, list):
        return
    seen: set[str] = set()
    for item in graph:
        if not isinstance(item, dict):
            continue
        spdx_id = item.get("spdxId")
        if not isinstance(spdx_id, str):
            continue
        if spdx_id in seen:
            raise ExporterError(f"SPDX AI exporter produced duplicate spdxId: {spdx_id}", "exporter")
        seen.add(spdx_id)


def _validate_spdx_ai_preview(payload: dict[str, object]) -> None:
    schema = resources.files("ai_bom_generator.exporters.spdx_ai.schema").joinpath(_LOCAL_SCHEMA)
    try:
        with resources.as_file(schema) as schema_path:
            validate_with_schema(payload, schema_path, "AI-BOM SPDX AI preview")
    except SchemaValidationError as exc:
        raise ExporterError(str(exc), "exporter") from exc
