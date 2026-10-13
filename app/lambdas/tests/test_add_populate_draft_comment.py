"""Tests for add_populate_draft_comment Lambda function.

This Lambda adds a comment to a workflow run indicating the current
populate-draft-data stage. It uses the orcabus_api_tools layer to post
comments, which we mock here.
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
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "add_populate_draft_comment_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.add_comment_to_workflow_run = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from add_populate_draft_comment import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables for the Lambda."""
    env_vars = {
        "WORKFLOW_NAME": "dragen-wgts-dna",
        "REPOSITORY_GITHUB_URL": "https://github.com/umccr/orcabus",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture(autouse=True)
def _reset_mock():
    """Reset the add_comment_to_workflow_run mock between tests."""
    _mock_workflow.add_comment_to_workflow_run.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestAddPopulateDraftCommentHappyPath:
    """Test the comment generation for various populate-draft stages."""

    def test_tags_changed_comment(self, event_builder, lambda_context):
        """commentType=tags_changed should post a tags-changed comment."""
        event = event_builder({
            "workflowRunId": "wfr.abc123",
            "commentType": "tags_changed",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-1",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}
        _mock_workflow.add_comment_to_workflow_run.assert_called_once()
        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert call_kwargs["workflow_run_orcabus_id"] == "wfr.abc123"
        assert "tags" in call_kwargs["comment"]

    def test_engine_parameters_changed_comment(self, event_builder, lambda_context):
        """commentType=engine_parameters_changed should mention engine parameters."""
        event = event_builder({
            "workflowRunId": "wfr.def456",
            "commentType": "engine_parameters_changed",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-2",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}
        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "engine parameters" in call_kwargs["comment"]

    def test_both_changed_comment(self, event_builder, lambda_context):
        """commentType=both_changed should mention both tags and engine parameters."""
        event = event_builder({
            "workflowRunId": "wfr.ghi789",
            "commentType": "both_changed",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-3",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}
        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "tags" in call_kwargs["comment"]
        assert "engine parameters" in call_kwargs["comment"]

    def test_updating_inputs_comment(self, event_builder, lambda_context):
        """commentType=updating_inputs should mention updating inputs."""
        event = event_builder({
            "workflowRunId": "wfr.jkl012",
            "commentType": "updating_inputs",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-4",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}
        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "inputs" in call_kwargs["comment"].lower()

    def test_no_change_missing_fields_comment(self, event_builder, lambda_context):
        """commentType=no_change_missing_fields should list missing fields."""
        event = event_builder({
            "workflowRunId": "wfr.mno345",
            "commentType": "no_change_missing_fields",
            "missingFields": ["inputs.sequenceData", "inputs.reference.tarball"],
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-5",
        })

        result = handler(event, lambda_context())

        assert result == {"commentAdded": True}
        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "inputs.sequenceData" in call_kwargs["comment"]
        assert "inputs.reference.tarball" in call_kwargs["comment"]


@pytest.mark.lambda_unit
class TestAddPopulateDraftCommentAuthor:
    """Test that the comment author is constructed correctly."""

    def test_author_contains_workflow_name(self, event_builder, lambda_context):
        """Author string should contain the workflow name."""
        event = event_builder({
            "workflowRunId": "wfr.test",
            "commentType": "updating_inputs",
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert "dragen-wgts-dna" in call_kwargs["author"]


@pytest.mark.lambda_unit
class TestAddPopulateDraftCommentFooter:
    """Test that the execution ARN footer is appended."""

    def test_execution_arn_in_comment(self, event_builder, lambda_context):
        """The execution ARN should appear in the comment footer."""
        arn = "arn:aws:states:ap-southeast-2:123456:execution:sfn:my-exec"
        event = event_builder({
            "workflowRunId": "wfr.footer",
            "commentType": "tags_changed",
            "executionArn": arn,
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert arn in call_kwargs["comment"]

    def test_long_comment_truncated(self, event_builder, lambda_context):
        """Comments exceeding 1024 chars should be truncated."""
        event = event_builder({
            "workflowRunId": "wfr.truncate",
            "commentType": "no_change_missing_fields",
            "missingFields": [f"inputs.field_{i}" for i in range(100)],
            "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:long-exec",
        })

        handler(event, lambda_context())

        call_kwargs = _mock_workflow.add_comment_to_workflow_run.call_args[1]
        assert len(call_kwargs["comment"]) <= 1024
