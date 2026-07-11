from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

from scripts import verify_release


SMOKE_REPOSITORY = "0disoft/ai-bom-generator-action-smoke"
SMOKE_WORKFLOW = "AI-BOM Smoke"
SMOKE_WORKFLOW_PATH = ".github/workflows/ai-bom-smoke.yml"
ACTION_REPOSITORY = "0disoft/ai-bom-generator"
RUN_ID = "12345"
HEAD_SHA = "a" * 40


class ReleaseVerificationTests(unittest.TestCase):
    def test_external_smoke_requires_exact_immutable_action_ref(self) -> None:
        workflow = _workflow_with_action_ref("v0.2.0")

        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[_successful_run(), _encoded_workflow(workflow)],
        ) as gh_json:
            verify_release._verify_external_smoke(
                SMOKE_REPOSITORY,
                SMOKE_WORKFLOW,
                SMOKE_WORKFLOW_PATH,
                RUN_ID,
                ACTION_REPOSITORY,
                "v0.2.0",
            )

        api_args = gh_json.call_args_list[1].args[0]
        self.assertEqual(
            api_args,
            [
                "api",
                f"repos/{SMOKE_REPOSITORY}/contents/.github/workflows/ai-bom-smoke.yml?ref={HEAD_SHA}",
            ],
        )

    def test_external_smoke_rejects_main_ref_even_when_run_succeeded(self) -> None:
        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[_successful_run(), _encoded_workflow(_workflow_with_action_ref("main"))],
        ):
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "must use exactly"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

    def test_external_smoke_rejects_multiple_target_action_refs(self) -> None:
        workflow = _workflow_with_action_ref("v0.2.0") + _workflow_with_action_ref("v0")
        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[_successful_run(), _encoded_workflow(workflow)],
        ):
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "must use exactly"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

    def test_external_smoke_rejects_run_from_another_workflow(self) -> None:
        run = _successful_run()
        run["workflowName"] = "Unrelated Workflow"
        with patch.object(verify_release, "_gh_json", return_value=run):
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "workflow mismatch"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

    def test_external_smoke_rejects_successful_run_without_head_sha(self) -> None:
        run = _successful_run()
        run["headSha"] = ""
        with patch.object(verify_release, "_gh_json", return_value=run) as gh_json:
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "missing headSha"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

        self.assertEqual(gh_json.call_count, 1)

    def test_external_smoke_rejects_failed_run_before_reading_workflow(self) -> None:
        run = _successful_run()
        run["conclusion"] = "failure"
        with patch.object(verify_release, "_gh_json", return_value=run) as gh_json:
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "did not succeed"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

        self.assertEqual(gh_json.call_count, 1)

    def test_external_smoke_rejects_non_file_workflow_response(self) -> None:
        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[_successful_run(), [{"type": "file"}]],
        ):
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "not base64 encoded"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

    def test_external_smoke_rejects_invalid_base64_workflow_content(self) -> None:
        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[
                _successful_run(),
                {"encoding": "base64", "content": "not-valid-base64%%%"},
            ],
        ):
            with self.assertRaisesRegex(verify_release.ReleaseVerificationError, "not valid base64 UTF-8"):
                verify_release._verify_external_smoke(
                    SMOKE_REPOSITORY,
                    SMOKE_WORKFLOW,
                    SMOKE_WORKFLOW_PATH,
                    RUN_ID,
                    ACTION_REPOSITORY,
                    "v0.2.0",
                )

    def test_external_smoke_resolves_latest_run_before_reading_workflow(self) -> None:
        with patch.object(
            verify_release,
            "_gh_json",
            side_effect=[
                [{"databaseId": 98765}],
                _successful_run(),
                _encoded_workflow(_workflow_with_action_ref("v0.2.0")),
            ],
        ) as gh_json:
            verify_release._verify_external_smoke(
                SMOKE_REPOSITORY,
                SMOKE_WORKFLOW,
                SMOKE_WORKFLOW_PATH,
                None,
                ACTION_REPOSITORY,
                "v0.2.0",
            )

        run_view_args = gh_json.call_args_list[1].args[0]
        self.assertEqual(run_view_args[0:3], ["run", "view", "98765"])


def _successful_run() -> dict[str, object]:
    return {
        "status": "completed",
        "conclusion": "success",
        "url": "https://example.invalid/run/12345",
        "headBranch": "main",
        "headSha": HEAD_SHA,
        "event": "push",
        "workflowName": SMOKE_WORKFLOW,
    }


def _encoded_workflow(workflow: str) -> dict[str, str]:
    return {
        "encoding": "base64",
        "content": base64.b64encode(workflow.encode("utf-8")).decode("ascii"),
    }


def _workflow_with_action_ref(ref: str) -> str:
    return (
        "jobs:\n"
        "  smoke:\n"
        "    steps:\n"
        "      - id: ai-bom\n"
        f"        uses: {ACTION_REPOSITORY}@{ref}\n"
    )


if __name__ == "__main__":
    unittest.main()
