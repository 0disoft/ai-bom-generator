from __future__ import annotations

from pathlib import Path
import random
import unittest

from ai_bom_generator.collectors.dependency_parsers import (
    DependencyParseError,
    DependencyParseResult,
    ParserLimits,
    parse_conda_lock,
    parse_pipenv_lock,
    parse_poetry_lock,
    parse_requirements,
    parse_uv_lock,
)
from ai_bom_generator.collectors.dependency_parsers.common import (
    bounded_artifact_hashes,
    parse_artifact_hash,
    source_revision,
)
from ai_bom_generator.domain.dependency import DependencyArtifactHash
from ai_bom_generator.security import Redactor


FIXTURES = Path(__file__).parent / "fixtures"
LIMITS = ParserLimits(
    max_packages=5_000,
    max_requirement_lines=10_000,
    max_artifact_hashes_per_package=256,
    max_conda_lock_channels=128,
    max_conda_lock_platforms=64,
    max_conda_lock_yaml_depth=64,
    max_pipenv_sources=128,
    max_pipenv_json_depth=64,
)
PARSERS = (
    ("requirements", parse_requirements, FIXTURES / "complete-project" / "requirements.lock"),
    ("uv", parse_uv_lock, FIXTURES / "dependency-lockfiles" / "uv.lock"),
    ("conda-lock", parse_conda_lock, FIXTURES / "conda-lock-corpus" / "official-shapes-v1.yml"),
    ("poetry", parse_poetry_lock, FIXTURES / "poetry-lock-corpus" / "poetry-2.1.lock"),
    ("pipenv", parse_pipenv_lock, FIXTURES / "pipenv-lock-corpus" / "pipenv-2026.6.2.lock"),
)


class DependencyParserPropertyTests(unittest.TestCase):
    def test_shared_hash_boundary_deduplicates_and_orders_before_enforcing_limit(self) -> None:
        hashes = [
            DependencyArtifactHash("sha512", "two", "https://example.invalid/two"),
            DependencyArtifactHash("sha256", "one", "https://example.invalid/one"),
            DependencyArtifactHash("sha512", "two", "https://example.invalid/two"),
        ]
        limited = ParserLimits(**{**LIMITS.__dict__, "max_artifact_hashes_per_package": 2})

        expected = (
            DependencyArtifactHash("sha256", "one", "https://example.invalid/one"),
            DependencyArtifactHash("sha512", "two", "https://example.invalid/two"),
        )
        for seed in range(16):
            shuffled = list(hashes)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(bounded_artifact_hashes(shuffled, limited), expected)

    def test_shared_hash_and_revision_parsers_fail_closed_on_ambiguous_input(self) -> None:
        redactor = Redactor("strict")
        self.assertEqual(
            parse_artifact_hash("SHA256:abc123", "https://example.invalid/file", redactor),
            DependencyArtifactHash("sha256", "abc123", "https://example.invalid/file"),
        )
        for value in (None, 1, "sha256", "sha256:", "sha256:a:b", " sha256:a b "):
            self.assertIsNone(parse_artifact_hash(value, None, redactor))

        cases = {
            "git+https://example.invalid/model.git@v1.2.3": "v1.2.3",
            "https://example.invalid/model.git?rev=abc123": "abc123",
            "https://example.invalid/model.git?tag=v2.0.0": "v2.0.0",
            "https://example.invalid/model.git?branch=main": "main",
            "https://example.invalid/model.git#deadbeef": "deadbeef",
            "https://example.invalid/model.git#subdirectory=src": None,
            "https://example.invalid/model.git": None,
        }
        for locator, expected in cases.items():
            with self.subTest(locator=locator):
                self.assertEqual(source_revision(locator), expected)

    def test_fixture_mutations_are_deterministic_and_never_leak_partial_invariants(self) -> None:
        for format_name, parser, fixture in PARSERS:
            baseline = fixture.read_bytes()
            for seed in range(32):
                payload = _mutate_payload(baseline, seed)
                with self.subTest(format=format_name, seed=seed):
                    first = _parse_outcome(parser, payload, format_name)
                    second = _parse_outcome(parser, payload, format_name)
                    self.assertEqual(first, second)
                    if isinstance(first, DependencyParseResult):
                        identities = [package.identity_key() for package in first.packages]
                        self.assertEqual(len(identities), len(set(identities)))
                        self.assertEqual(
                            list(first.packages),
                            sorted(
                                first.packages,
                                key=lambda item: (
                                    item.source.path,
                                    item.name,
                                    item.version or "",
                                    item.requirement,
                                ),
                            ),
                        )


def _mutate_payload(payload: bytes, seed: int) -> bytes:
    rng = random.Random(seed)
    operation = seed % 3
    if operation == 0:
        index = rng.randrange(len(payload))
        replacement = rng.choice((0, 10, 34, 39, 91, 93, 123, 125, 255))
        return payload[:index] + bytes((replacement,)) + payload[index + 1 :]
    if operation == 1:
        return payload[: rng.randrange(len(payload) + 1)]
    index = rng.randrange(len(payload) + 1)
    insertion = rng.choice((b"\x00", b"\xff", b"[]", b"{}", b"=", b"\n"))
    return payload[:index] + insertion + payload[index:]


def _parse_outcome(parser, payload: bytes, format_name: str):
    try:
        return parser(payload, f"mutated.{format_name}", Redactor("strict"), LIMITS)
    except DependencyParseError as exc:
        return (type(exc).__name__, str(exc))


if __name__ == "__main__":
    unittest.main()
