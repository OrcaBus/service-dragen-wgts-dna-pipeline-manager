"""Tests for convert_icav2_wes_state_change_event_to_wrsc_event Lambda function.

This Lambda converts an ICAv2 WES state change event into a WorkflowRunStateChange
event. It looks up the workflow run by portal run ID and constructs the WRSC payload.
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
    / "convert_icav2_wes_state_change_event_to_wrsc_event_py"
)

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.get_workflow_run_from_portal_run_id = MagicMock()
_mock_workflow.get_latest_payload_from_workflow_run = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from convert_icav2_wes_state_change_event_to_wrsc_event import handler  # noqa: E402


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------


def _make_workflow_run(portal_run_id="20250606efgh1234"):
    """Build a minimal workflow run object as returned by the API."""
    return {
        "orcabusId": "wfr.abc123",
        "portalRunId": portal_run_id,
        "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--" + portal_run_id,
        "workflow": {
            "workflowName": "dragen-wgts-dna",
            "workflowVersion": "4.4.4",
        },
        "libraries": [
            {"libraryId": "L2301197", "orcabusId": "lib.ABC123"}
        ],
        "linkedLibraries": [
            {"libraryId": "L2301197", "orcabusId": "lib.ABC123"}
        ],
    }


def _make_payload():
    """Build a minimal latest payload object."""
    return {
        "version": "2025.06.04",
        "data": {
            "inputs": {
                "sampleName": "L2301197",
                "reference": {"name": "hg38", "structure": "linear"},
            },
            "engineParameters": {
                "pipelineId": "pipe-123",
                "projectId": "proj-456",
                "outputUri": "s3://bucket/output/",
                "logsUri": "s3://bucket/logs/",
            },
            "tags": {"libraryId": "L2301197"},
        },
    }


def _make_icav2_wes_event(status="RUNNING", portal_run_id="20250606efgh1234"):
    """Build a minimal ICAv2 WES state change event."""
    return {
        "icav2WesStateChangeEvent": {
            "id": "iwa.01JWAGE5PWS5JN48VWNPYSTJRN",
            "name": f"umccr--automated--dragen-wgts-dna--4-4-4--{portal_run_id}",
            "status": status,
            "tags": {"portalRunId": portal_run_id, "libraryId": "L2301197"},
            "icav2AnalysisId": "analysis-789",
            "inputs": {},
            "engineParameters": {},
        }
    }


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks and provide default return values."""
    _mock_workflow.get_workflow_run_from_portal_run_id.reset_mock()
    _mock_workflow.get_latest_payload_from_workflow_run.reset_mock()
    _mock_workflow.get_workflow_run_from_portal_run_id.return_value = _make_workflow_run()
    _mock_workflow.get_latest_payload_from_workflow_run.return_value = _make_payload()
    yield


# ---------------------------------------------------------------------------
# Tests: RUNNING status
# ---------------------------------------------------------------------------


@pytest.mark.lambda_unit
class TestConvertRunningEvent:
    """Test conversion of a RUNNING status event."""

    def test_output_contains_wrsc_event(self, event_builder, lambda_context):
        """Output should contain workflowRunStateChangeEvent key."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        assert "workflowRunStateChangeEvent" in result

    def test_status_is_running(self, event_builder, lambda_context):
        """Status should be RUNNING."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        assert result["workflowRunStateChangeEvent"]["status"] == "RUNNING"

    def test_portal_run_id_preserved(self, event_builder, lambda_context):
        """Portal run ID should be preserved from the event tags."""
        event = _make_icav2_wes_event(status="RUNNING", portal_run_id="20250601test1234")
        _mock_workflow.get_workflow_run_from_portal_run_id.return_value = _make_workflow_run("20250601test1234")

        result = handler(event, lambda_context())

        assert result["workflowRunStateChangeEvent"]["portalRunId"] == "20250601test1234"

    def test_workflow_details_present(self, event_builder, lambda_context):
        """Workflow name and version should be in the output."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        wrsc = result["workflowRunStateChangeEvent"]
        assert wrsc["workflow"]["name"] == "dragen-wgts-dna"
        assert wrsc["workflow"]["version"] == "4.4.4"

    def test_libraries_preserved(self, event_builder, lambda_context):
        """Libraries from the workflow run should be preserved."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        assert result["workflowRunStateChangeEvent"]["libraries"] == [
            {"libraryId": "L2301197", "orcabusId": "lib.ABC123"}
        ]

    def test_no_error_fields_for_running(self, event_builder, lambda_context):
        """RUNNING events should have null error fields."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        assert result["errorMessageUri"] is None
        assert result["errorType"] is None

    def test_execution_id_set(self, event_builder, lambda_context):
        """executionId should be set from icav2AnalysisId."""
        event = _make_icav2_wes_event(status="RUNNING")

        result = handler(event, lambda_context())

        assert result["workflowRunStateChangeEvent"]["executionId"] == "analysis-789"


# ---------------------------------------------------------------------------
# Tests: SUCCEEDED status
# ---------------------------------------------------------------------------


@pytest.mark.lambda_unit
class TestConvertSucceededEvent:
    """Test conversion of a SUCCEEDED status event."""

    def test_outputs_generated_for_germline(self, event_builder, lambda_context):
        """SUCCEEDED should generate output paths for germline variant calling."""
        event = _make_icav2_wes_event(status="SUCCEEDED")

        result = handler(event, lambda_context())

        payload_data = result["workflowRunStateChangeEvent"]["payload"]["data"]
        assert "outputs" in payload_data
        assert "dragenGermlineVariantCallingOutputRelPath" in payload_data["outputs"]
        assert payload_data["outputs"]["dragenGermlineVariantCallingOutputRelPath"] == (
            "L2301197__hg38__linear__dragen_wgts_dna_germline_variant_calling/"
        )

    def test_somatic_output_for_tumor_normal(self, event_builder, lambda_context):
        """SUCCEEDED with tumor sample should generate somatic output paths."""
        payload = _make_payload()
        payload["data"]["inputs"]["tumorSampleName"] = "T2301198"
        _mock_workflow.get_latest_payload_from_workflow_run.return_value = payload

        event = _make_icav2_wes_event(status="SUCCEEDED")

        result = handler(event, lambda_context())

        payload_data = result["workflowRunStateChangeEvent"]["payload"]["data"]
        assert "dragenSomaticVariantCallingOutputRelPath" in payload_data["outputs"]
        assert "T2301198" in payload_data["outputs"]["dragenSomaticVariantCallingOutputRelPath"]

    def test_multiqc_output_for_germline(self, event_builder, lambda_context):
        """SUCCEEDED germline should generate multiQc output path."""
        event = _make_icav2_wes_event(status="SUCCEEDED")

        result = handler(event, lambda_context())

        payload_data = result["workflowRunStateChangeEvent"]["payload"]["data"]
        assert payload_data["outputs"]["multiQcOutputRelPath"] == "L2301197_multiqc/"


# ---------------------------------------------------------------------------
# Tests: FAILED status
# ---------------------------------------------------------------------------


@pytest.mark.lambda_unit
class TestConvertFailedEvent:
    """Test conversion of a FAILED status event."""

    def test_error_fields_populated(self, event_builder, lambda_context):
        """FAILED events should have errorType and errorMessageUri populated."""
        event = _make_icav2_wes_event(status="FAILED")
        event["icav2WesStateChangeEvent"]["errorType"] = "TaskFailed"
        event["icav2WesStateChangeEvent"]["errorMessageUri"] = "s3://bucket/error.log"

        result = handler(event, lambda_context())

        assert result["errorType"] == "TaskFailed"
        assert result["errorMessageUri"] == "s3://bucket/error.log"

    def test_status_is_failed(self, event_builder, lambda_context):
        """Status should be FAILED."""
        event = _make_icav2_wes_event(status="FAILED")
        event["icav2WesStateChangeEvent"]["errorType"] = "TaskFailed"

        result = handler(event, lambda_context())

        assert result["workflowRunStateChangeEvent"]["status"] == "FAILED"
