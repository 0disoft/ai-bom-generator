from __future__ import annotations

from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_github_action import _require_exact_action_pin  # noqa: E402


class GitHubActionVerificationTests(unittest.TestCase):
    def test_exact_action_pin_accepts_updated_patch_version(self) -> None:
        text = "  uses: astral-sh/setup-uv@v8.3.2\n"

        ref = _require_exact_action_pin(text, "astral-sh/setup-uv")

        self.assertEqual(ref, "v8.3.2")

    def test_exact_action_pin_rejects_floating_major_tag(self) -> None:
        text = "  uses: astral-sh/setup-uv@v8\n"

        with self.assertRaisesRegex(AssertionError, "exact vMAJOR.MINOR.PATCH"):
            _require_exact_action_pin(text, "astral-sh/setup-uv")

    def test_exact_action_pin_rejects_duplicate_uses(self) -> None:
        text = (
            "  uses: astral-sh/setup-uv@v8.3.1\n"
            "  uses: astral-sh/setup-uv@v8.3.2\n"
        )

        with self.assertRaisesRegex(AssertionError, "exactly once; found 2"):
            _require_exact_action_pin(text, "astral-sh/setup-uv")


if __name__ == "__main__":
    unittest.main()
