"""Tests for get_missing_schema_fields Lambda function.

This Lambda validates payload data against a JSON schema and returns the list
of missing/invalid fields. It fetches the schema from AWS (SSM + Schema Registry),
which we patch here.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_missing_schema_fields_py"

sys.path.insert(0, str(LAMBDA_DIR))

from get_missing_schema_fields import handler  # noqa: E402

# Sample schema for tests
SAMPLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["sampleName", "reference", "sequenceData"],
    "properties": {
        "sampleName": {"type": "string", "minLength": 1},
        "reference": {
            "type": "object",
            "required": ["name", "tarball"],
            "properties": {
                "name": {"type": "string"},
                "tarball": {"type": "string", "pattern": "^s3://"},
            },
        },
        "sequenceData": {
            "type": "object",
            "required": ["fastqListRows"],
            "properties": {
                "fastqListRows": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["rgid", "read1FileUri"],
                        "properties": {
                            "rgid": {"type": "string"},
                            "read1FileUri": {"type": "string", "pattern": "^s3://"},
                        },
                    },
                }
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
        "DEFAULT_PAYLOAD_VERSION": "2025.06.04",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture(autouse=True)
def _mock_aws():
    """Patch SSM and Schema Registry calls."""
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
        patch("get_missing_schema_fields.get_ssm_parameter_value", side_effect=ssm_side_effect),
        patch(
            "get_missing_schema_fields.get_schema_from_registry",
            return_value=json.dumps(SAMPLE_SCHEMA),
        ),
    ):
        yield


@pytest.mark.lambda_unit
class TestGetMissingSchemaFieldsValid:
    """Test cases where the payload is valid — no missing fields."""

    def test_complete_payload_no_missing_fields(self, event_builder, lambda_context):
        """A fully valid payload should return an empty missingFields list."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleName": "SMP001",
                "reference": {"name": "hg38", "tarball": "s3://bucket/ref.tar.gz"},
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RGID001", "read1FileUri": "s3://bucket/r1.fq.gz"}
                    ]
                },
            },
        })

        result = handler(event, lambda_context())

        assert result["missingFields"] == []


@pytest.mark.lambda_unit
class TestGetMissingSchemaFieldsMissing:
    """Test cases where the payload is missing required fields."""

    def test_missing_top_level_field(self, event_builder, lambda_context):
        """Missing 'sampleName' should appear in missingFields."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                # Missing sampleName
                "reference": {"name": "hg38", "tarball": "s3://bucket/ref.tar.gz"},
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RGID001", "read1FileUri": "s3://bucket/r1.fq.gz"}
                    ]
                },
            },
        })

        result = handler(event, lambda_context())

        assert any("sampleName" in f for f in result["missingFields"])

    def test_missing_nested_field(self, event_builder, lambda_context):
        """Missing 'reference.tarball' should appear in missingFields."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleName": "SMP001",
                "reference": {"name": "hg38"},  # Missing tarball
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RGID001", "read1FileUri": "s3://bucket/r1.fq.gz"}
                    ]
                },
            },
        })

        result = handler(event, lambda_context())

        assert any("tarball" in f for f in result["missingFields"])

    def test_missing_multiple_fields(self, event_builder, lambda_context):
        """Multiple missing fields should all be reported."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {},  # Missing everything
        })

        result = handler(event, lambda_context())

        assert len(result["missingFields"]) >= 3  # sampleName, reference, sequenceData

    def test_invalid_type_reported(self, event_builder, lambda_context):
        """A wrong type should be reported in missingFields."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleName": 123,  # Should be string
                "reference": {"name": "hg38", "tarball": "s3://bucket/ref.tar.gz"},
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RGID001", "read1FileUri": "s3://bucket/r1.fq.gz"}
                    ]
                },
            },
        })

        result = handler(event, lambda_context())

        # Should report the type error for sampleName
        assert len(result["missingFields"]) > 0

    def test_empty_fastq_list_rows(self, event_builder, lambda_context):
        """An empty fastqListRows array should trigger a validation error."""
        event = event_builder({
            "payloadVersion": "2025.06.04",
            "data": {
                "sampleName": "SMP001",
                "reference": {"name": "hg38", "tarball": "s3://bucket/ref.tar.gz"},
                "sequenceData": {"fastqListRows": []},  # minItems = 1
            },
        })

        result = handler(event, lambda_context())

        assert len(result["missingFields"]) > 0
