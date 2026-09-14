"""Verified, run-local cache for the three public SPDX 3.0.1 resources."""
from functools import lru_cache
from hashlib import sha256
import json
from urllib.request import urlopen


RESOURCES = {
    "context": ("https://spdx.org/rdf/3.0.1/spdx-context.jsonld", "c72b0928f094c83e5c127784edb1ebca2af74a104fcacc007c332b23cbc788bd"),
    "model": ("https://spdx.org/rdf/3.0.1/spdx-model.ttl", "30ebb4af2d70a9809044ef46f44cc3dc5125226d70f818a50ed2e1d5f404c593"),
    "schema": ("https://spdx.org/schema/3.0.1/spdx-json-schema.json", "582c64e809d5b3ef9bd0c4de13a32391b47b0284a3e8d199569fb96f649234b1"),
}
MAX_RESOURCE_BYTES = 2 * 1024 * 1024


class ResourceError(RuntimeError):
    """Infrastructure or reviewed-resource drift, not a BOM mapping failure."""


@lru_cache(maxsize=3)
def resource(name: str) -> str:
    url, expected = RESOURCES[name]
    try:
        with urlopen(url, timeout=30) as response:
            data = response.read(MAX_RESOURCE_BYTES + 1)
    except (OSError, TimeoutError) as exc:
        raise ResourceError(f"resource-network-error: {name} ({type(exc).__name__})") from exc
    if len(data) > MAX_RESOURCE_BYTES:
        raise ResourceError(f"resource-size-error: {name}")
    if sha256(data).hexdigest() != expected:
        raise ResourceError(f"resource-integrity-error: {name}; review upstream changes before updating digest")
    return data.decode("utf-8")


class UpstreamValidator:
    def __init__(self) -> None:
        import rdflib
        from spdx3_validate.core import schema_validator
        from spdx3_validate.spdx_versions import find_version

        self.version = find_version(RESOURCES["context"][0])
        if self.version is None:
            raise ResourceError("validator-version-error: SPDX 3.0.1 unavailable")
        self.context = json.loads(resource("context"))["@context"]
        self.schema = schema_validator(json.loads(resource("schema")))
        self.model = rdflib.Graph().parse(data=resource("model"), format="turtle")

    def errors(self, path) -> list[str]:
        import rdflib
        from spdx3_validate.core import check_graph

        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("@context") != RESOURCES["context"][0]:
            raise ResourceError("fixture-context-error: only the reviewed context is allowed")
        errors = [f"schema: {error.message}" for error in self.schema.iter_errors(data)]
        # Expand using the verified in-memory context. No repeated remote context fetch.
        local = {**data, "@context": self.context}
        graph = rdflib.Graph().parse(data=json.dumps(local), format="json-ld")
        errors.extend(f"shacl: {error}" for error in check_graph(graph, self.model, self.version, True))
        return errors
