from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_github_action import _require_exact_action_pin, _verify_external_action_pins  # noqa: E402
import github_action_entrypoint  # noqa: E402

from ai_bom_generator.reporting.json_writer import write_json_output_set  # noqa: E402


class GitHubActionVerificationTests(unittest.TestCase):
    def test_repository_external_actions_are_sha_pinned(self) -> None:
        _verify_external_action_pins()

    def test_nonzero_exit_does_not_publish_verified_stale_summary_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            output = work / "bom.json"
            warning_report = work / "warnings.json"
            summary = work / "summary.json"
            manifest = work / "manifest.json"
            github_output = work / "github-output.txt"
            write_json_output_set(
                [
                    ("bom", output, {"old_run": True}),
                    ("warning_report", warning_report, {"warning_count": 0}),
                    (
                        "summary",
                        summary,
                        {
                            "status": "success",
                            "warning_count": 0,
                            "completeness_status": "complete",
                            "format": "cyclonedx-json-1.7",
                        },
                    ),
                ],
                manifest,
            )
            previous = os.environ.get("GITHUB_OUTPUT")
            os.environ["GITHUB_OUTPUT"] = str(github_output)
            try:
                github_action_entrypoint._write_outputs(
                    output,
                    warning_report,
                    summary,
                    manifest,
                    exit_code=40,
                )
            finally:
                if previous is None:
                    os.environ.pop("GITHUB_OUTPUT", None)
                else:
                    os.environ["GITHUB_OUTPUT"] = previous

            text = github_output.read_text(encoding="utf-8")
            self.assertIn("\n40\n", text)
            self.assertNotIn("status<<", text)
            self.assertNotIn("warning-count<<", text)
            self.assertNotIn("completeness-status<<", text)
            self.assertNotIn("format<<", text)

    def test_exact_action_pin_accepts_sha_with_version_comment(self) -> None:
        sha = "11f9893b081a58869d3b5fccaea48c9e9e46f990"
        text = f"  uses: astral-sh/setup-uv@{sha} # v8.3.2\n"

        ref = _require_exact_action_pin(text, "astral-sh/setup-uv")

        self.assertEqual(ref, sha)

    def test_exact_action_pin_rejects_floating_major_tag(self) -> None:
        text = "  uses: astral-sh/setup-uv@v8\n"

        with self.assertRaisesRegex(AssertionError, "full commit SHA"):
            _require_exact_action_pin(text, "astral-sh/setup-uv")

    def test_exact_action_pin_rejects_sha_without_version_comment(self) -> None:
        text = "  uses: astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990\n"

        with self.assertRaisesRegex(AssertionError, "semver comment"):
            _require_exact_action_pin(text, "astral-sh/setup-uv")

    def test_exact_action_pin_rejects_duplicate_uses(self) -> None:
        text = (
            "  uses: astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990 # v8.3.1\n"
            "  uses: astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990 # v8.3.2\n"
        )

        with self.assertRaisesRegex(AssertionError, "found 2"):
            _require_exact_action_pin(text, "astral-sh/setup-uv")


if __name__ == "__main__":
    unittest.main()
