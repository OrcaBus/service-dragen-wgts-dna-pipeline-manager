"""Tests for compare_payload Lambda function."""

import sys
from pathlib import Path

import pytest

# Path setup for Lambda handler import
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "compare_payload_py"
sys.path.insert(0, str(LAMBDA_DIR))

from compare_payload import handler  # noqa: E402


@pytest.mark.lambda_unit
class TestComparePayloadIdentical:
    """Test cases where payloads are identical (hasChanged=False)."""

    def test_identical_simple_payloads(self, event_builder, lambda_context):
        """Two identical flat payloads should return hasChanged=False."""
        payload = {"key": "value", "number": 42}
        event = event_builder({"oldPayload": payload, "newPayload": payload})
        ctx = lambda_context(function_name="compare-payload")

        result = handler(event, ctx)

        assert result == {"hasChanged": False}

    def test_identical_nested_payloads(self, event_builder, lambda_context):
        """Two identical nested payloads should return hasChanged=False."""
        payload = {
            "inputs": {
                "sampleName": "SMP001",
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RG001", "lane": 1, "read1FileUri": "s3://bucket/r1.fq.gz"}
                    ]
                },
            },
            "engineParameters": {"pipelineId": "pipeline-123", "projectId": "proj-456"},
        }
        event = event_builder({"oldPayload": payload, "newPayload": payload})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": False}

    def test_identical_empty_payloads(self, event_builder, lambda_context):
        """Two empty payloads should return hasChanged=False."""
        event = event_builder({"oldPayload": {}, "newPayload": {}})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": False}


@pytest.mark.lambda_unit
class TestComparePayloadChanged:
    """Test cases where payloads differ (hasChanged=True)."""

    def test_added_key(self, event_builder, lambda_context):
        """New payload with an additional key should return hasChanged=True."""
        old = {"key": "value"}
        new = {"key": "value", "extra": "data"}
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}

    def test_removed_key(self, event_builder, lambda_context):
        """New payload with a removed key should return hasChanged=True."""
        old = {"key": "value", "extra": "data"}
        new = {"key": "value"}
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}

    def test_changed_value(self, event_builder, lambda_context):
        """New payload with a changed value should return hasChanged=True."""
        old = {"pipelineId": "pipeline-old"}
        new = {"pipelineId": "pipeline-new"}
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}

    def test_changed_nested_value(self, event_builder, lambda_context):
        """A change deep in a nested structure should be detected."""
        old = {
            "inputs": {
                "sequenceData": {"fastqListRows": [{"rgid": "RG001", "lane": 1}]}
            }
        }
        new = {
            "inputs": {
                "sequenceData": {"fastqListRows": [{"rgid": "RG001", "lane": 2}]}
            }
        }
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}

    def test_changed_list_order(self, event_builder, lambda_context):
        """A reordered list should be detected as a change (order-sensitive)."""
        old = {"items": [1, 2, 3]}
        new = {"items": [3, 2, 1]}
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}

    def test_type_change(self, event_builder, lambda_context):
        """Changing a value type (string to int) should be detected."""
        old = {"count": "42"}
        new = {"count": 42}
        event = event_builder({"oldPayload": old, "newPayload": new})
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result == {"hasChanged": True}
