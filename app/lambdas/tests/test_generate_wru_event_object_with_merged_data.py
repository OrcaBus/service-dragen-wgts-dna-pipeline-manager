"""Tests for generate_wru_event_object_with_merged_data Lambda function.

This Lambda constructs a WorkflowRunUpdate event object by merging the current
payload data with the workflow run metadata from the API.
"""

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
    / "generate_wru_event_object_with_merged_data_py"
)

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.get_workflow_run_from_portal_run_id = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from generate_wru_event_object_with_merged_data import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks and set default return value."""
    _mock_workflow.get_workflow_run_from_portal_run_id.reset_mock()
    _mock_workflow.get_workflow_run_from_portal_run_id.return_value = {
        "orcabusId": "wfr.abc123",
        "portalRunId": "20250606efgh1234",
        "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606efgh1234",
        "workflow": {"workflowName": "dragen-wgts-dna", "workflowVersion": "4.4.4"},
        "linkedLibraries": [{"libraryId": "L2301197", "orcabusId": "lib.ABC123"}],
    }
    yield


@pytest.mark.lambda_unit
class TestGenerateWruEventObjectHappyPath:
    """Test the happy path for generating a WRU event object."""

    def test_output_contains_workflow_run_update(self, event_builder, lambda_context):
        """Output should contain workflowRunUpdate key."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [{"libraryId": "L2301197", "orcabusId": "lib.ABC123", "readsets": []}],
            "payload": {"version": "2025.06.04", "data": {"inputs": {}, "tags": {}}},
        })

        result = handler(event, lambda_context())

        assert "workflowRunUpdate" in result

    def test_orcabus_id_from_api(self, event_builder, lambda_context):
        """The orcabusId should come from the API lookup."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        result = handler(event, lambda_context())

        assert result["workflowRunUpdate"]["orcabusId"] == "wfr.abc123"

    def test_status_is_draft(self, event_builder, lambda_context):
        """The status should always be DRAFT."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        result = handler(event, lambda_context())

        assert result["workflowRunUpdate"]["status"] == "DRAFT"

    def test_workflow_preserved_from_api(self, event_builder, lambda_context):
        """The workflow field should come from the API."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        result = handler(event, lambda_context())

        assert result["workflowRunUpdate"]["workflow"] == {
            "workflowName": "dragen-wgts-dna",
            "workflowVersion": "4.4.4",
        }

    def test_libraries_structured_correctly(self, event_builder, lambda_context):
        """Libraries should be structured with libraryId, orcabusId, readsets."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [
                {
                    "libraryId": "L2301197",
                    "orcabusId": "lib.ABC123",
                    "readsets": [{"orcabusId": "rs.001", "rgid": "RGID001"}],
                }
            ],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        result = handler(event, lambda_context())

        libs = result["workflowRunUpdate"]["libraries"]
        assert len(libs) == 1
        assert libs[0]["libraryId"] == "L2301197"
        assert libs[0]["orcabusId"] == "lib.ABC123"
        assert libs[0]["readsets"] == [{"orcabusId": "rs.001", "rgid": "RGID001"}]

    def test_payload_passed_through(self, event_builder, lambda_context):
        """The payload from the input should be passed through to the output."""
        payload = {
            "version": "2025.06.04",
            "data": {
                "inputs": {"sampleName": "SMP001"},
                "tags": {"libraryId": "L2301197"},
            },
        }
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [],
            "payload": payload,
        })

        result = handler(event, lambda_context())

        assert result["workflowRunUpdate"]["payload"] == payload

    def test_linked_libraries_from_api(self, event_builder, lambda_context):
        """linkedLibraries should come from the API workflow run."""
        event = event_builder({
            "portalRunId": "20250606efgh1234",
            "libraries": [],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        result = handler(event, lambda_context())

        assert result["workflowRunUpdate"]["linkedLibraries"] == [
            {"libraryId": "L2301197", "orcabusId": "lib.ABC123"}
        ]

    def test_portal_run_id_looked_up(self, event_builder, lambda_context):
        """The handler should look up the workflow run by portal run ID."""
        event = event_builder({
            "portalRunId": "20250601test5678",
            "libraries": [],
            "payload": {"version": "2025.06.04", "data": {}},
        })

        handler(event, lambda_context())

        _mock_workflow.get_workflow_run_from_portal_run_id.assert_called_once_with(
            portal_run_id="20250601test5678"
        )
