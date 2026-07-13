from __future__ import annotations

import unittest

from ai_bom_generator.domain.dependency import (
    DependencyArtifactHash,
    DependencyPackage,
    DependencySourceEvidence,
)
from ai_bom_generator.domain.source_location import SourceLocation
from ai_bom_generator.exporters.cyclonedx_json.mapper import _dependency_package_properties
from ai_bom_generator.exporters.spdx_ai.mapper import _dependency_package_element


class DependencySourceEvidenceTests(unittest.TestCase):
    def test_all_source_evidence_fields_reach_both_exporter_boundaries(self) -> None:
        package = DependencyPackage(
            name="example-package",
            version="1.0.0",
            requirement="example-package==1.0.0",
            lockfile_format="future-lock",
            package_source=DependencySourceEvidence(
                source_type="conda",
                locator="https://example.invalid/channel/linux-64/example-package.conda",
                channel="example-channel",
                index="https://example.invalid/channel",
                platform="linux-64",
                revision="build-7",
                artifact_hashes=(
                    DependencyArtifactHash(
                        algorithm="sha256",
                        value="synthetic",
                        locator="https://example.invalid/channel/linux-64/example-package.conda",
                    ),
                ),
            ),
            marker=None,
            extras=(),
            source=SourceLocation(path="future.lock", field="package[0]", collector="dependency"),
        )

        cyclonedx = {item["name"]: item["value"] for item in _dependency_package_properties(package)}
        self.assertEqual(cyclonedx["ai-bom:dependency:source-channel"], "example-channel")
        self.assertEqual(cyclonedx["ai-bom:dependency:source-index"], "https://example.invalid/channel")
        self.assertEqual(cyclonedx["ai-bom:dependency:source-platform"], "linux-64")
        self.assertEqual(cyclonedx["ai-bom:dependency:source-revision"], "build-7")
        self.assertEqual(cyclonedx["ai-bom:dependency:artifact:0:hash"], "sha256:synthetic")

        spdx = _dependency_package_element(package, "urn:ai-bom-generator:spdx-ai:creation-info")
        self.assertEqual(spdx["aiBom:sourceChannel"], "example-channel")
        self.assertEqual(spdx["aiBom:sourceIndex"], "https://example.invalid/channel")
        self.assertEqual(spdx["aiBom:sourcePlatform"], "linux-64")
        self.assertEqual(spdx["aiBom:sourceRevision"], "build-7")
        self.assertEqual(
            spdx["aiBom:artifactHashes"],
            [
                {
                    "algorithm": "sha256",
                    "hashValue": "synthetic",
                    "locator": "https://example.invalid/channel/linux-64/example-package.conda",
                }
            ],
        )

    def test_source_evidence_changes_package_identity(self) -> None:
        base = DependencySourceEvidence(source_type="registry", index="https://example.invalid/simple")
        changed = DependencySourceEvidence(
            source_type="registry",
            index="https://example.invalid/simple",
            platform="linux-64",
        )

        self.assertNotEqual(base.identity_key(), changed.identity_key())


if __name__ == "__main__":
    unittest.main()
