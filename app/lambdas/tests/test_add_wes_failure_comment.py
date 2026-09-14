"""Tests for add_wes_failure_comment Lambda function.

This Lambda posts a comment to the workflow run when an ICA analysis has failed.
It looks up the workflow run from the portal run ID, then posts a comment with
the error type and error message URI.
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
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "add_wes_failure_comment_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.add_comment_to_workflow_run = MagicMock()
_mock_workflow.get_workflow_run_from_portal_run_id = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from add_wes_failure_comment import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables for the Lambda."""
    with patch.dict(os.environ, {"WORKFLOW_NAME": "dragen-wgts-dna"}):
        yield


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_workflow.add_comment_to_workflow_run.reset_mock()
    _mock_workflow.get_workflow_run_from_portal_run_id.reset_mock()
    # Default return value for workflow run lookup
    _mock_workflow.get_workflow_run_from_portal_run_id.return_value = {
        "orcabusId": "wfr.resolved123",
        "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
    }
    yield


@pytest.mark.lambda_unit
class TestAddWesFailureCommentHappyPath:
    """Test the failure comment generation."""

    def test_returns_expected_structure(self, event_builder, lambda_context):
        """Handler should return status, portalRunId, and workflowRunId."""
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": "s3://bucket/errors/error.log",
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-1",
        })

        result = handler(event, lambda_context())

        assert result["status"] == "comment_added"
        assert result["portalRunId"] == "20250601abcd1234"  # pragma: allowlist secret
        assert result["workflowRunId"] == "wfr.resolved123"

    def test_comment_contains_error_type(self, event_builder, lambda_context):
        """The posted comment should mention the error type."""
        event = event_builder({
            "errorType": "AnalysisTimeout",
            "errorMessageUri": "s3://bucket/errors/timeout.log",
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-2",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "AnalysisTimeout" in call_kwargs["comment"]

    def test_comment_contains_error_message_uri(self, event_builder, lambda_context):
        """The posted comment should mention the error message URI."""
        error_uri = "s3://bucket/errors/my-error.log"
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": error_uri,
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-3",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert error_uri in call_kwargs["comment"]

    def test_workflow_run_looked_up_by_portal_run_id(self, event_builder, lambda_context):
        """The handler should look up the workflow run using the portal run ID."""
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": "s3://bucket/errors/error.log",
            "portalRunId": "20250601efgh5678",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-4",
        })

        handler(event, lambda_context())

        _mock_workflow.get_workflow_run_from_portal_run_id.assert_called_once_with(
            "20250601efgh5678"
        )

    def test_execution_arn_in_comment_footer(self, event_builder, lambda_context):
        """The execution ARN should appear in the comment footer."""
        arn = "arn:aws:states:ap-southeast-2:123456:execution:sfn:my-exec"
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": "s3://bucket/errors/error.log",
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": arn,
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert arn in call_kwargs["comment"]

    def test_author_contains_workflow_name(self, event_builder, lambda_context):
        """The comment author should contain the workflow name."""
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": "s3://bucket/errors/error.log",
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "dragen-wgts-dna" in call_kwargs["author"]


@pytest.mark.lambda_unit
class TestAddWesFailureCommentTruncation:
    """Test that long comments are truncated to 1024 chars."""

    def test_long_error_message_uri_truncated(self, event_builder, lambda_context):
        """A very long error message URI should result in a truncated comment."""
        long_uri = "s3://bucket/errors/" + "a" * 2000 + ".log"
        event = event_builder({
            "errorType": "TaskFailed",
            "errorMessageUri": long_uri,
            "portalRunId": "20250601abcd1234",  # pragma: allowlist secret
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert len(call_kwargs["comment"]) <= 1024
