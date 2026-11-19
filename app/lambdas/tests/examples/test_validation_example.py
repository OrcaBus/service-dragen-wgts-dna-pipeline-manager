"""
Example: Testing a Schema Validation Lambda
============================================

This template demonstrates how to test a Lambda function that validates
input data against a JSON schema. The Lambda fetches its schema from AWS
services (SSM + Schemas Registry) at runtime, so we patch those data-fetching
functions to inject a known schema for testing.

Pattern:
    - Patch functions that fetch configuration from AWS (SSM, Schema Registry)
    - Provide a test JSON schema inline
    - Call handler with valid data → assert isValid=True
    - Call handler with invalid data → assert isValid=False
    - Test specific validation failures (missing fields, wrong types)

Real-world example: validate_draft_complete_schema_py
    - Fetches schema registry name from SSM
    - Fetches schema from AWS Schemas Registry
    - Validates event payload against the JSON schema
    - Returns {"isValid": true/false}

Fixtures used:
    - event_builder: Wraps a dict payload into a Lambda event
    - lambda_context: Provides a mock Lambda context object

Note: Since moto does not fully support the AWS Schemas Registry service,
we patch the individual helper functions (get_ssm_parameter_value,
get_schema_from_registry) rather than mocking the entire AWS service.
This approach is simpler and more resilient to moto version changes.
"""

import json
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup
#
# The validate_draft_complete_schema Lambda uses the `orcabus_api_tools`
# layer package. We mock it before importing the handler.
# ---------------------------------------------------------------------------
LAMBDA_DIR = (
    Path(__file__).resolve().parents[2] / "validate_draft_complete_schema_py"
)

# Mock the Lambda Layer dependency (orcabus_api_tools)
_mock_api_tools = MagicMock()
sys.modules.setdefault("orcabus_api_tools", _mock_api_tools)
sys.modules.setdefault("orcabus_api_tools.workflow", _mock_api_tools.workflow)

sys.path.insert(0, str(LAMBDA_DIR))

from validate_draft_complete_schema import handler  # noqa: E402


# ---------------------------------------------------------------------------
# Test JSON Schema — a simplified version of the real draft schema
# ---------------------------------------------------------------------------

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
                    "read1FileUri": {
                        "type": "string",
                        "pattern": "^s3://",
                    },
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Fixtures specific to this test module
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables for the Lambda."""
    env_vars = {
        "SSM_REGISTRY_NAME": "/orcabus/schemas/registry-name",
        "SSM_SCHEMA_PATH": "/orcabus/workflows/dragen-wgts-dna/schema",
        "WORKFLOW_NAME": "dragen-wgts-dna",
        "DEFAULT_PAYLOAD_VERSION": "2025.08.05",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture(autouse=True)
def _mock_aws_calls():
    """Patch the AWS service calls to return controlled test data.

    This patches:
    - get_ssm_parameter_value → returns registry name or schema name JSON
    - get_schema_from_registry → returns our test schema
    - add_comment_to_workflow_run → no-op (we test it was called separately)
    """
    def ssm_side_effect(parameter_name: str) -> str:
        """Simulate SSM parameter lookups."""
        params = {
            "/orcabus/schemas/registry-name": "OrcaBusSchemaRegistry",
            "/orcabus/workflows/dragen-wgts-dna/schema/2025.08.05": json.dumps(
                {"schemaName": "dragen-wgts-dna-draft-v2025.08.05"}
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
        patch(
            "validate_draft_complete_schema.add_comment_to_workflow_run",
        ) as mock_comment,
    ):
        yield mock_comment


# ---------------------------------------------------------------------------
# Tests: Valid inputs
# ---------------------------------------------------------------------------


class TestValidPayloads:
    """Test that valid payloads pass schema validation."""

    def test_valid_minimal_payload(self, event_builder, lambda_context):
        """A payload with all required fields passes validation."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001.1.AACTGAGG.AACTGAGG",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/path/read1.fastq.gz",
                    }
                ],
            },
        })
        ctx = lambda_context(function_name="validate-draft-complete-schema")

        result = handler(event, ctx)

        assert result["isValid"] is True

    def test_valid_payload_multiple_fastq_rows(self, event_builder, lambda_context):
        """A payload with multiple FASTQ rows passes validation."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001.1.AACTGAGG",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/lane1/read1.fastq.gz",
                    },
                    {
                        "rgid": "RGID001.2.AACTGAGG",
                        "rgsm": "SMP001",
                        "lane": 2,
                        "read1FileUri": "s3://bucket/lane2/read1.fastq.gz",
                    },
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is True


# ---------------------------------------------------------------------------
# Tests: Invalid inputs
# ---------------------------------------------------------------------------


class TestInvalidPayloads:
    """Test that invalid payloads fail schema validation with isValid=False."""

    def test_missing_required_field(self, event_builder, lambda_context):
        """A payload missing 'sampleId' fails validation."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                # Missing sampleId
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/read1.fastq.gz",
                    }
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False

    def test_wrong_type_for_field(self, event_builder, lambda_context):
        """A payload with wrong type for 'lane' (string instead of integer) fails."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001",
                        "rgsm": "SMP001",
                        "lane": "one",  # Should be an integer
                        "read1FileUri": "s3://bucket/read1.fastq.gz",
                    }
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False

    def test_empty_fastq_list_rows(self, event_builder, lambda_context):
        """A payload with an empty fastqListRows array fails minItems validation."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [],  # Must have at least 1 item
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False

    def test_invalid_uri_pattern(self, event_builder, lambda_context):
        """A read1FileUri that doesn't start with s3:// fails pattern validation."""
        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                "sampleId": "SMP001",
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "https://bucket/read1.fastq.gz",  # Not s3://
                    }
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False


# ---------------------------------------------------------------------------
# Tests: Error comment behaviour
# ---------------------------------------------------------------------------


class TestErrorCommentBehaviour:
    """Test that validation failure comments are posted when requested."""

    def test_comment_added_on_error_when_flag_set(
        self, _mock_aws_calls, event_builder, lambda_context
    ):
        """When addCommentOnError=True and validation fails, a comment is posted."""
        mock_comment = _mock_aws_calls

        event = event_builder({
            "payloadVersion": "2025.08.05",
            "workflowRunId": "wfr.abc123",
            "addCommentOnError": True,
            "data": {
                # Missing sampleId to trigger validation failure
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/read1.fastq.gz",
                    }
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False
        # Verify the comment API was called with the workflow run ID
        mock_comment.assert_called_once()
        call_kwargs = mock_comment.call_args
        assert "wfr.abc123" in str(call_kwargs)

    def test_no_comment_when_flag_not_set(
        self, _mock_aws_calls, event_builder, lambda_context
    ):
        """When addCommentOnError is False (default), no comment is posted on failure."""
        mock_comment = _mock_aws_calls

        event = event_builder({
            "payloadVersion": "2025.08.05",
            "data": {
                # Missing sampleId to trigger validation failure
                "libraryId": "L2401001",
                "fastqListRows": [
                    {
                        "rgid": "RGID001",
                        "rgsm": "SMP001",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/read1.fastq.gz",
                    }
                ],
            },
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["isValid"] is False
        mock_comment.assert_not_called()
