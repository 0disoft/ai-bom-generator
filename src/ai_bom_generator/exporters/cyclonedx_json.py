from __future__ import annotations

from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.errors import ExporterError
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
    return redacted


def _model_properties(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    properties: list[dict[str, str]] = [
        {"name": "ai-bom:completeness-status", "value": evidence.completeness_status},
        {"name": "ai-bom:warning-count", "value": str(evidence.warning_count)},
    ]
    for reference in evidence.model_metadata:
        for key, value in reference.values:
            properties.append({"name": f"ai-bom:model:{key}", "value": value})
    return sorted(properties, key=lambda item: item["name"])
