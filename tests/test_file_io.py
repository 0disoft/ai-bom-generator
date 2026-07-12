from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_bom_generator.security import file_io
from ai_bom_generator.security.file_io import open_binary_nofollow


class FileIoTests(unittest.TestCase):
    def test_safe_open_rejects_path_replaced_between_lstat_and_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            candidate = work / "candidate.txt"
            replacement = work / "replacement.txt"
            candidate.write_text("safe", encoding="utf-8")
            replacement.write_text("replacement", encoding="utf-8")
            real_open = file_io.os.open
            swapped = False

            def swap_then_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped:
                    os.replace(replacement, candidate)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with patch.object(file_io.os, "open", side_effect=swap_then_open):
                with self.assertRaisesRegex(OSError, "changed before it could be opened safely"):
                    with open_binary_nofollow(candidate):
                        self.fail("replaced file must not be exposed to the caller")

    def test_safe_open_reads_stable_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.txt"
            path.write_bytes(b"stable")

            with open_binary_nofollow(path) as handle:
                self.assertEqual(handle.read(), b"stable")


if __name__ == "__main__":
    unittest.main()
