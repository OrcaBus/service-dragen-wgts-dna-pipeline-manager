"""Tests for validate_draft_complete_schema Lambda function.

This Lambda validates a draft payload against a JSON schema fetched from
AWS Schema Registry. We patch the SSM and Schema Registry calls.
"""

import json
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools and boto3 layers
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "validate_draft_complete_schema_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.add_comment_to_workflow_run = MagicMock()
_mock_api_tools.workflow = _mock_workflow

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow

sys.path.insert(0, str(LAMBDA_DIR))

from validate_draft_complete_schema import handler  # noqa: E402


# Test JSON schema
SAMPLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["sampleId", "libraryId", "fastqListRows"],
    "properties": {
        "sampleId": {"type": "string", "minLength": 1},
        "libraryId": {"type": "string", "minLength": 1},
        "fastqListRows": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["rgid", "rgsm", "lane", "read1FileUri"],
                "properties": {
                    "rgid": {"type": "string"},
                    "rgsm": {"type": "string"},
                    "lane": {"type": "integer", "minimum": 1},
                    "read1FileUri": {"type": "string", "pattern": "^s3://"},
                },
            },
        },
    },
}


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables."""
    env_vars = {
        "SSM_REGISTRY_NAME": "/orcabus/schemas/registry-name",
        "SSM_SCHEMA_PATH": "/orcabus/workflows/dragen-wgts-dna/schema",
        "WORKFLOW_NAME": "dragen-wgts-dna",
        "DEFAULT_PAYLOAD_VERSION": "2025.06.04",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture(autouse=True)
def _mock_aws():
    """Patch AWS service calls."""
    def ssm_side_effect(parameter_name):
        params = {
            "/orcabus/schemas/registry-name": "OrcaBusSchemaRegistry",
            "/orcabus/workflows/dragen-wgts-dna/schema/2025.06.04": json.dumps(
                {"schemaName": "dragen-wgts-dna-draft-v2025.06.04"}
            ),
        }
        if parameter_name in params:
            return params[parameter_name]
        raise ValueError(f"Unknown SSM parameter: {parameter_name}")

    with (
        patch(
            "validate_draft_complete_schema.get_ssm_parameter_value",
            side_effect=ssm_side_effect,
        ),
        patch(
            "validate_draft_complete_schema.get_schema_from_registry",
            return_value=json.dumps(SAMPLE_SCHEMA),
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset comment mock between tests."""
    _mock_workflow.add_comment_to_workflow_run.reset_mock()
    yield


@pytest.fixture()
def mock_add_comment():
    """Patch the add_comment_to_workflow_run at the handler module level."""
    with patch("validate_draft_complete_schema.add_comment_to_workflow_run") as mock_comment:
        yield mock_comment


@pytest.mark.lambda_unit
class TestValidateValidPayloads:
    """Test that valid payloads pass validation."""

    def test_valid_minimal_payload(self, event_builder, lambda_context):
        """A payload with all required fields passes validation."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001.1.RUN",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/r1.fastq.gz",
                    }
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": True}

    def test_valid_multiple_rows(self, event_builder, lambda_context):
        """A payload with multiple FASTQ rows passes validation."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "s3://b/r1.fq"},
                    {"rgid": "RG2", "rgsm": "SMP001", "lane": 2, "read1FileUri": "s3://b/r2.fq"},
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": True}


@pytest.mark.lambda_unit
class TestValidateInvalidPayloads:
    """Test that invalid payloads fail validation."""

    def test_missing_required_field(self, event_builder, lambda_context):
        """Missing 'sampleId' should fail validation."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "s3://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}

    def test_wrong_type_for_lane(self, event_builder, lambda_context):
        """String lane instead of integer should fail validation."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": "one", "read1FileUri": "s3://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}

    def test_empty_fastq_list(self, event_builder, lambda_context):
        """Empty fastqListRows should fail minItems validation."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}

    def test_invalid_uri_pattern(self, event_builder, lambda_context):
        """read1FileUri not starting with s3:// should fail."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "https://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}


@pytest.mark.lambda_unit
class TestValidateCommentOnError:
    """Test that validation failures post comments when requested."""

    def test_comment_posted_when_flag_true(self, mock_add_comment, event_builder, lambda_context):
        """When addCommentOnError=True and validation fails, a comment is posted."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "workflowRunId": "wfr.abc123",
            "addCommentOnError": True,
            "data": {
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "s3://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}
        mock_add_comment.assert_called_once()
        call_kwargs = mock_add_comment.call_args[1]
        assert "wfr.abc123" in str(call_kwargs)

    def test_no_comment_when_flag_false(self, mock_add_comment, event_builder, lambda_context):
        """When addCommentOnError is not set, no comment is posted."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "s3://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": False}
        mock_add_comment.assert_not_called()

    def test_no_comment_on_valid_payload(self, mock_add_comment, event_builder, lambda_context):
        """Even with addCommentOnError=True, no comment on valid payload."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "workflowRunId": "wfr.abc123",
            "addCommentOnError": True,
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {"rgid": "RG1", "rgsm": "SMP001", "lane": 1, "read1FileUri": "s3://b/r1.fq"}
                ],
            },
        })

        result = handler(event, lambda_context())

        assert result == {"isValid": True}
        mock_add_comment.assert_not_called()
