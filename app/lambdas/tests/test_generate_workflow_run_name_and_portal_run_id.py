"""Tests for generate_workflow_run_name_and_portal_run_id Lambda function.

This Lambda generates a portal run ID and workflow run name by calling
orcabus_api_tools.workflow utilities. The generated names follow a
deterministic format based on workflow name, version, and portal run ID.
"""

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.workflow layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = (
    Path(__file__).resolve().parents[1]
    / "generate_workflow_run_name_and_portal_run_id_py"
)

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.create_portal_run_id = MagicMock()
_mock_workflow.create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from generate_workflow_run_name_and_portal_run_id import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables for the Lambda."""
    env_vars = {
        "WORKFLOW_NAME": "dragen-wgts-dna",
        "WORKFLOW_VERSION": "4.4.4",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_workflow.create_portal_run_id.reset_mock()
    _mock_workflow.create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id.reset_mock()
    # Set default return values
    _mock_workflow.create_portal_run_id.return_value = "20250606abcd1234"
    _mock_workflow.create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id.return_value = (
        "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd1234"
    )
    yield


@pytest.mark.lambda_unit
class TestGenerateWorkflowRunNameAndPortalRunId:
    """Test the workflow run name and portal run ID generation."""

    def test_returns_portal_run_id(self, event_builder, lambda_context):
        """Handler should return the generated portalRunId."""
        event = event_builder({})

        result = handler(event, lambda_context())

        assert result["portalRunId"] == "20250606abcd1234"  # pragma: allowlist secret

    def test_returns_workflow_run_name(self, event_builder, lambda_context):
        """Handler should return the generated workflowRunName."""
        event = event_builder({})

        result = handler(event, lambda_context())

        assert result["workflowRunName"] == (
            "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd1234"
        )

    def test_calls_create_portal_run_id(self, event_builder, lambda_context):
        """Handler should call create_portal_run_id."""
        event = event_builder({})

        handler(event, lambda_context())

        _mock_workflow.create_portal_run_id.assert_called_once()

    def test_calls_create_workflow_run_name_with_correct_args(self, event_builder, lambda_context):
        """Handler should call create_workflow_run_name with env var values."""
        event = event_builder({})

        handler(event, lambda_context())

        _mock_workflow.create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id.assert_called_once_with(
            workflow_name="dragen-wgts-dna",
            workflow_version="4.4.4",
            portal_run_id="20250606abcd1234",
        )

    def test_different_workflow_version(self, event_builder, lambda_context):
        """Handler should use the WORKFLOW_VERSION env var."""
        _mock_workflow.create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id.return_value = (
            "umccr--automated--dragen-wgts-dna--5-0-0--20250606abcd1234"
        )

        with patch.dict(os.environ, {"WORKFLOW_VERSION": "5.0.0"}):
            event = event_builder({})
            result = handler(event, lambda_context())

        assert "5-0-0" in result["workflowRunName"]
