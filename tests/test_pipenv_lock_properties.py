from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest

from ai_bom_generator.collectors.dependency_files import (
    DependencyFileLimitError,
    DependencyParseError,
    parse_dependency_file,
)
from ai_bom_generator.security import Redactor


FUZZ_SEED = 0xA1B0_600
SHAPE_CASES = 256
EVIDENCE_CASES = 120


class PipenvLockPropertyTests(unittest.TestCase):
    def test_seeded_json_shapes_fail_only_with_domain_errors(self) -> None:
        rng = random.Random(FUZZ_SEED)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Pipfile.lock"
            for case_index in range(SHAPE_CASES):
                document = _random_document(rng)
                path.write_text(
                    json.dumps(document, separators=(",", ":")),
                    encoding="utf-8",
                    newline="\n",
                )

                try:
                    result = parse_dependency_file(
                        path,
                        "Pipfile.lock",
                        "pipenv",
                        Redactor("strict"),
                    )
                except (DependencyParseError, DependencyFileLimitError):
                    continue
                except Exception as exc:  # pragma: no cover - assertion reports the generated case
                    self.fail(
                        f"seed {FUZZ_SEED} case {case_index} escaped the parser domain: "
                        f"{type(exc).__name__}: {exc}; document={document!r}"
                    )

                for package in result.packages:
                    self.assertTrue(package.name)
                    self.assertTrue(package.requirement)
                    self.assertEqual(package.lockfile_format, "pipenv")
                    self.assertEqual(package.source.path, "Pipfile.lock")

    def test_generated_entries_do_not_fabricate_versions_sources_markers_or_hashes(self) -> None:
        versions: tuple[tuple[object, str | None], ...] = (
            ("==1.2.3", "1.2.3"),
            (">=1,<2", None),
            ("==1.*", None),
            ("*", None),
            ("not-a-specifier", None),
            (7, None),
        )
        entries: dict[str, object] = {}
        expectations: dict[str, tuple[str | None, str, str | None, str | None, int]] = {}

        for index in range(EVIDENCE_CASES):
            name = f"generated-package-{index}"
            version, exact_version = versions[index % len(versions)]
            entry: dict[str, object] = {"version": version}

            source_case = index % 3
            if source_case == 0:
                entry.update(
                    {
                        "git": f"https://example.invalid/generated-{index}.git",
                        "path": f"packages/generated-{index}",
                    }
                )
                source_type = "unknown"
                source_locator = None
            elif source_case == 1:
                entry["index"] = f"missing-index-{index}"
                source_type = "registry"
                source_locator = None
            else:
                entry["file"] = 7
                source_type = "file"
                source_locator = None

            if index % 2 == 0:
                entry["markers"] = "python_version >= '3.12'"
                marker = "python_version >= '3.12'"
            else:
                entry["markers"] = "definitely not a marker"
                marker = None

            if index % 4 == 0:
                entry["hashes"] = ["not-a-hash"]
                hash_count = 0
            else:
                entry["hashes"] = [f"sha256:{index:064x}"]
                hash_count = 1

            entries[name] = entry
            expectations[name] = (exact_version, source_type, source_locator, marker, hash_count)

        document = {
            "_meta": {
                "pipfile-spec": 6,
                "sources": [
                    {"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}
                ],
            },
            "default": entries,
            "develop": {},
        }

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Pipfile.lock"
            path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
            result = parse_dependency_file(
                path,
                "Pipfile.lock",
                "pipenv",
                Redactor("strict"),
            )

        self.assertEqual(len(result.packages), EVIDENCE_CASES)
        self.assertGreater(result.skipped_entries, 0)
        for package in result.packages:
            exact_version, source_type, source_locator, marker, hash_count = expectations[
                package.name
            ]
            self.assertEqual(package.version, exact_version)
            self.assertEqual(package.source_type, source_type)
            self.assertEqual(package.source_locator, source_locator)
            self.assertEqual(package.marker, marker)
            self.assertEqual(len(package.package_source.artifact_hashes), hash_count)


def _random_document(rng: random.Random) -> object:
    if rng.randrange(4) == 0:
        return _random_json_value(rng, 0)
    return {
        "_meta": rng.choice(
            [
                {"pipfile-spec": 6, "sources": _random_json_value(rng, 1)},
                {"pipfile-spec": rng.choice([None, True, 5, 7, "6"])},
                _random_json_value(rng, 1),
            ]
        ),
        "default": _random_json_value(rng, 0),
        "develop": _random_json_value(rng, 0),
    }


def _random_json_value(rng: random.Random, depth: int) -> object:
    atoms: tuple[object, ...] = (
        None,
        True,
        False,
        -1,
        0,
        6,
        "",
        "==1.2.3",
        "not-a-marker",
        "https://example.invalid/package",
    )
    if depth >= 3:
        return rng.choice(atoms)
    kind = rng.randrange(3)
    if kind == 0:
        return rng.choice(atoms)
    if kind == 1:
        return [_random_json_value(rng, depth + 1) for _ in range(rng.randrange(5))]
    keys = (
        "package",
        "valid-package",
        "version",
        "markers",
        "hashes",
        "git",
        "file",
        "path",
        "index",
        "extras",
        "editable",
        "sources",
    )
    return {
        rng.choice(keys): _random_json_value(rng, depth + 1)
        for _ in range(rng.randrange(5))
    }


if __name__ == "__main__":
    unittest.main()
