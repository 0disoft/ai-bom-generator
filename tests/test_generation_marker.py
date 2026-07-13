from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.app import GenerateBomOptions, generate_bom
from ai_bom_generator.collectors import collect_evidence
from ai_bom_generator.collectors.generation_marker import (
    MAX_GENERATION_MARKER_BYTES,
    collect_initial_generation_marker,
    verify_final_generation_marker,
)
from ai_bom_generator.config import load_config
from ai_bom_generator.errors import CollectorError, InvalidInputError
from ai_bom_generator.exporters.cyclonedx_json import export_cyclonedx_json
from ai_bom_generator.exporters.spdx_ai import export_spdx_ai
from ai_bom_generator.security import PathPolicy, Redactor


class GenerationMarkerTests(unittest.TestCase):
    def test_complete_marker_is_digest_only_provenance_in_both_exporters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, config, marker = _project(Path(temp))
            payload = _marker_payload("private-generation-value")
            marker.write_bytes(payload)
            evidence = collect_evidence(load_config(config, PathPolicy(root)), PathPolicy(root), Redactor("strict"))

            self.assertIsNotNone(evidence.generation_marker)
            assert evidence.generation_marker is not None
            self.assertEqual(evidence.generation_marker.path, "generation.json")
            self.assertEqual(evidence.generation_marker.digest, sha256(payload).hexdigest())

            cyclonedx = export_cyclonedx_json(evidence, Redactor("strict"))
            spdx = export_spdx_ai(evidence, Redactor("strict"))
            serialized = json.dumps([cyclonedx, spdx], sort_keys=True)
            self.assertNotIn("private-generation-value", serialized)
            self.assertIn(sha256(payload).hexdigest(), serialized)
            self.assertIn("generation.json", serialized)

    def test_initial_marker_must_be_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, config, marker = _project(Path(temp))
            marker.write_bytes(_marker_payload("generation-1", state="writing"))

            with self.assertRaisesRegex(InvalidInputError, 'state must be "complete"'):
                collect_initial_generation_marker(load_config(config, PathPolicy(root)), PathPolicy(root))

    def test_initial_marker_rejects_malformed_duplicate_and_oversized_payloads(self) -> None:
        payloads = (
            b"not-json",
            b'{"schema_version":"1","generation":"a","generation":"b","state":"complete"}',
            b" " * (MAX_GENERATION_MARKER_BYTES + 1),
        )
        for payload in payloads:
            with self.subTest(payload_size=len(payload)), tempfile.TemporaryDirectory() as temp:
                root, config, marker = _project(Path(temp))
                marker.write_bytes(payload)

                with self.assertRaises(InvalidInputError):
                    collect_initial_generation_marker(load_config(config, PathPolicy(root)), PathPolicy(root))

    def test_marker_must_stay_inside_target_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            root, config, _ = _project(work, marker_path="../outside.json")
            (work / "outside.json").write_bytes(_marker_payload("generation-1"))

            with self.assertRaisesRegex(InvalidInputError, "Path escapes target root"):
                collect_initial_generation_marker(load_config(config, PathPolicy(root)), PathPolicy(root))

    def test_marker_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            root, config, marker = _project(work)
            target = root / "real-generation.json"
            target.write_bytes(_marker_payload("generation-1"))
            try:
                marker.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            with self.assertRaisesRegex(InvalidInputError, "Symlink file is not allowed"):
                collect_initial_generation_marker(load_config(config, PathPolicy(root)), PathPolicy(root))

    def test_marker_change_during_collection_is_a_collector_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, config, marker = _project(Path(temp))
            marker.write_bytes(_marker_payload("generation-1"))
            loaded = load_config(config, PathPolicy(root))
            initial = collect_initial_generation_marker(loaded, PathPolicy(root))
            marker.write_bytes(_marker_payload("generation-2"))

            with self.assertRaisesRegex(CollectorError, "changed during collection"):
                verify_final_generation_marker(loaded, PathPolicy(root), initial)

    def test_final_marker_missing_or_writing_is_a_collector_failure(self) -> None:
        for final_state in ("missing", "writing"):
            with self.subTest(final_state=final_state), tempfile.TemporaryDirectory() as temp:
                root, config, marker = _project(Path(temp))
                marker.write_bytes(_marker_payload("generation-1"))
                loaded = load_config(config, PathPolicy(root))
                initial = collect_initial_generation_marker(loaded, PathPolicy(root))
                if final_state == "missing":
                    marker.unlink()
                else:
                    marker.write_bytes(_marker_payload("generation-2", state="writing"))

                with self.assertRaises(CollectorError):
                    verify_final_generation_marker(loaded, PathPolicy(root), initial)

    def test_marker_failure_preserves_previous_committed_output_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            root, config, marker = _project(work)
            marker.write_bytes(_marker_payload("generation-1"))
            options = GenerateBomOptions(
                model_directory=root,
                config=config,
                output_format="cyclonedx-json-1.7",
                output=work / "bom.json",
                warning_report=work / "warnings.json",
                summary=work / "summary.json",
                manifest=work / "manifest.json",
                summary_stdout=False,
                warnings="allow",
                redaction="strict",
            )
            self.assertEqual(generate_bom(options), 0)
            previous = {
                path.name: path.read_bytes()
                for path in (options.output, options.warning_report, options.summary, options.manifest)
                if path is not None
            }

            from ai_bom_generator.collectors import pipeline

            original_collect_git = pipeline._collect_git

            def collect_git_then_start_write(policy, warnings):
                result = original_collect_git(policy, warnings)
                marker.write_bytes(_marker_payload("generation-2", state="writing"))
                return result

            with patch.object(pipeline, "_collect_git", side_effect=collect_git_then_start_write):
                with self.assertRaises(CollectorError):
                    generate_bom(options)

            current = {
                path.name: path.read_bytes()
                for path in (options.output, options.warning_report, options.summary, options.manifest)
                if path is not None
            }
            self.assertEqual(current, previous)


def _project(work: Path, marker_path: str = "generation.json") -> tuple[Path, Path, Path]:
    root = work / "project"
    root.mkdir()
    config = root / "aibom.toml"
    config.write_text(
        'schema_version = "1"\n\n'
        '[generation]\n'
        f'marker = "{marker_path}"\n\n'
        '[model]\n'
        'name = "marker-model"\n'
        'license_declared = "NOASSERTION"\n',
        encoding="utf-8",
    )
    return root, config, root / "generation.json"


def _marker_payload(generation: str, state: str = "complete") -> bytes:
    return json.dumps(
        {"schema_version": "1", "generation": generation, "state": state},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
