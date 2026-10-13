t"""Tests for add_ready_comment Lambda function.

This Lambda adds a comment to a workflow run indicating the READY-to-SUBMITTED
transition has started. It uses the orcabus_api_tools layer to post comments.
"""

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools layer before importing handler
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "add_ready_comment_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.add_comment_to_workflow_run = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from add_ready_comment import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables for the Lambda."""
    with patch.dict(os.environ, {"WORKFLOW_NAME": "dragen-wgts-dna"}):
        yield


@pytest.fixture(autouse=True)
def _reset_mock():
    """Reset the add_comment_to_workflow_run mock between tests."""
    _mock_workflow.add_comment_to_workflow_run.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestAddReadyCommentHappyPath:
    """Test the happy-path comment generation."""

    def test_returns_comment_added_true(self, event_builder, lambda_context):
        """Handler should return commentAdded=True on success."""
        event = event_builder({
            "workflowRunId": "wfr.ready123",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-1",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}

    def test_comment_mentions_ready_to_submitted(self, event_builder, lambda_context):
        """Comment body should mention the READY-to-SUBMITTED transition."""
        event = event_builder({
            "workflowRunId": "wfr.ready456",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-2",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "READY" in call_kwargs["comment"]
        assert "SUBMITTED" in call_kwargs["comment"]

    def test_workflow_run_id_passed_correctly(self, event_builder, lambda_context):
        """The workflow_run_orcabus_id should match the input workflowRunId."""
        event = event_builder({
            "workflowRunId": "wfr.specific789",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-3",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert call_kwargs["workflow_run_orcabus_id"] == "wfr.specific789"

    def test_execution_arn_in_footer(self, event_builder, lambda_context):
        """The execution ARN should appear in the comment."""
        arn = "arn:aws:states:ap-southeast-2:123456:execution:sfn:my-exec"
        event = event_builder({
            "workflowRunId": "wfr.footer",
            "executionArn": arn,
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert arn in call_kwargs["comment"]

    def test_author_contains_workflow_name(self, event_builder, lambda_context):
        """The comment author should contain the workflow name."""
        event = event_builder({
            "workflowRunId": "wfr.author",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "dragen-wgts-dna" in call_kwargs["author"]


@pytest.mark.lambda_unit
class TestAddReadyCommentTruncation:
    """Test comment truncation behaviour."""

    def test_short_comment_not_truncated(self, event_builder, lambda_context):
        """A normal comment should not be truncated."""
        event = event_builder({
            "workflowRunId": "wfr.short",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert len(call_kwargs["comment"]) <= 1024
        assert "[truncated" not in call_kwargs["comment"]
