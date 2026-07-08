from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.errors import CollectorError
from ai_bom_generator.hashing import sha256_file, sha256_file_snapshot


class HashingTests(unittest.TestCase):
    def test_sha256_file_matches_standard_digest_with_chunked_reads(self) -> None:
        payload = b"model-bytes-" * 257
        expected = hashlib.sha256(payload).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.safetensors"
            artifact.write_bytes(payload)

            digest = sha256_file(artifact, chunk_size=17)
            snapshot = sha256_file_snapshot(artifact, chunk_size=17)

        self.assertEqual(digest, expected)
        self.assertEqual(snapshot.digest, expected)
        self.assertEqual(snapshot.digest_algorithm, "sha256")
        self.assertEqual(snapshot.size, len(payload))

    def test_sha256_file_rejects_invalid_chunk_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.safetensors"
            artifact.write_bytes(b"content")

            with self.assertRaises(CollectorError) as error:
                sha256_file(artifact, chunk_size=0)

        self.assertEqual(error.exception.stage, "hash")
        self.assertIn("chunk_size must be positive", error.exception.message)

    def test_sha256_file_wraps_read_failures_as_collector_errors(self) -> None:
        with self.assertRaises(CollectorError) as error:
            sha256_file(FailingPath("model.safetensors"))

        self.assertEqual(error.exception.stage, "hash")
        self.assertIn("Failed to hash artifact model.safetensors", error.exception.message)

    def test_sha256_file_snapshot_rejects_file_changes_during_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.safetensors"
            artifact.write_bytes(b"stable-at-open")
            before = FakeStat(size=len(b"stable-at-open"), modified_ns=100, changed_ns=100)
            after = FakeStat(size=len(b"changed-after-open"), modified_ns=200, changed_ns=200)

            with (
                patch("ai_bom_generator.hashing.sha256.os.fstat", side_effect=[before, after]),
                self.assertRaises(CollectorError) as error,
            ):
                sha256_file_snapshot(artifact)

        self.assertEqual(error.exception.stage, "hash")
        self.assertIn("Artifact changed while hashing", error.exception.message)


class FailingPath:
    def __init__(self, name: str) -> None:
        self.name = name

    def open(self, mode: str) -> None:
        raise OSError("synthetic read failure")

    def __str__(self) -> str:
        return self.name


class FakeStat:
    def __init__(self, size: int, modified_ns: int, changed_ns: int) -> None:
        self.st_dev = 1
        self.st_ino = 2
        self.st_size = size
        self.st_mtime_ns = modified_ns
        self.st_ctime_ns = changed_ns


if __name__ == "__main__":
    unittest.main()
