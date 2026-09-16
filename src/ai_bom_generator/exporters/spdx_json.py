"""Bounded SPDX 3.0.1 Core/Software/AI mapping; no runtime network access."""
from hashlib import sha256
import json

from ai_bom_generator.config.spdx_document import DocumentMetadata
from ai_bom_generator import __version__
from ai_bom_generator.domain.evidence import NormalizedEvidence
from ai_bom_generator.exporters.spdx_ai import export_spdx_ai
from ai_bom_generator.security import Redactor


SUPPORTED_FORMAT = "spdx-json-3.0.1"


def export_spdx_json(evidence: NormalizedEvidence, redactor: Redactor, metadata: DocumentMetadata) -> dict:
    preview = export_spdx_ai(evidence, redactor)
    author = redactor.redact_text(metadata.creator_name)
    # Namespace is tied to redacted evidence and explicit document metadata, never host identity.
    seed = json.dumps([preview, metadata.created, author, metadata.creator_type], sort_keys=True)
    namespace = "urn:aibom:spdx:" + sha256(seed.encode()).hexdigest() + ":"
    source = preview["@graph"]
    mapped = {item["spdxId"]: namespace + sha256(item["spdxId"].encode()).hexdigest()
              for item in source if item.get("type") in ("ai_AIPackage", "software_File", "software_Package")}
    creation = "_:creation"
    creator = namespace + "creator"
    tool = namespace + "tool"
    graph = [
        {"type": "CreationInfo", "@id": creation, "specVersion": "3.0.1",
         "created": metadata.created, "createdBy": [creator], "createdUsing": [tool]},
        {"type": metadata.creator_type, "spdxId": creator, "creationInfo": creation, "name": author},
        {"type": "Tool", "spdxId": tool, "creationInfo": creation, "name": f"ai-bom-generator {__version__}"},
    ]
    model_id = None
    for item in source:
        if item["spdxId"] not in mapped:
            continue
        element = {"type": item["type"], "spdxId": mapped[item["spdxId"]],
                   "creationInfo": creation, "name": item["name"]}
        version = item.get("packageVersion")
        if version and version != "NOASSERTION":
            element["software_packageVersion"] = version
        if item["type"] == "software_File":
            element["verifiedUsing"] = [
                {"type": "Hash", "algorithm": "sha256", "hashValue": digest["hashValue"]}
                for digest in item.get("verifiedUsing", []) if digest["algorithm"] == "SHA256"
            ]
        # Preserve extension evidence as redacted JSON text, not unknown JSON-LD predicates.
        mapped_fields = {"type", "spdxId", "creationInfo", "name", "packageVersion", "verifiedUsing"}
        extra = {key: value for key, value in item.items() if key not in mapped_fields}
        if extra:
            element["comment"] = json.dumps(extra, sort_keys=True, ensure_ascii=False)
        if item["type"] == "ai_AIPackage":
            model_id = element["spdxId"]
        graph.append(element)
    assert model_id is not None
    for kind, relation in (("software_File", "contains"), ("software_Package", "dependsOn")):
        targets = sorted(item["spdxId"] for item in graph if item["type"] == kind)
        if targets:
            graph.append({"type": "Relationship", "spdxId": namespace + relation,
                          "creationInfo": creation, "from": model_id, "to": targets,
                          "relationshipType": relation, "completeness": "noAssertion"})
    references = [item for item in source if item["type"] == "aiBom_Reference"]
    graph.append({"type": "SpdxDocument", "spdxId": namespace + "document",
                  "creationInfo": creation, "rootElement": [model_id],
                  "element": sorted(item["spdxId"] for item in graph if "spdxId" in item),
                  "profileConformance": ["core", "software", "ai"],
                  "comment": json.dumps({"declaredReferences": references,
                                        "mappingScope": "Core/Software/AI; other evidence retained as comments"},
                                       sort_keys=True, ensure_ascii=False)})
    return {"@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
            "@graph": sorted(graph, key=lambda item: item.get("spdxId", item.get("@id", "")))}
