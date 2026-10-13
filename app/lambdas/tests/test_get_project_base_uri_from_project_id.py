"""Tests for get_project_base_uri_from_project_id Lambda function.

This Lambda retrieves the S3 base URI for an ICAv2 project by its project ID.
It uses wrapica and icav2_tools layers.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock wrapica and icav2_tools layers
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_project_base_uri_from_project_id_py"

# Mock wrapica
_mock_wrapica = ModuleType("wrapica")
_mock_storage_config = ModuleType("wrapica.storage_configuration")
_mock_storage_config.get_s3_key_prefix_by_project_id = MagicMock()
_mock_wrapica.storage_configuration = _mock_storage_config

# Mock icav2_tools
_mock_icav2_tools = ModuleType("icav2_tools")
_mock_icav2_tools.set_icav2_env_vars = MagicMock()

sys.modules["wrapica"] = _mock_wrapica
sys.modules["wrapica.storage_configuration"] = _mock_storage_config
sys.modules["icav2_tools"] = _mock_icav2_tools

sys.path.insert(0, str(LAMBDA_DIR))

from get_project_base_uri_from_project_id import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_storage_config.get_s3_key_prefix_by_project_id.reset_mock()
    _mock_icav2_tools.set_icav2_env_vars.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestGetProjectBaseUriHappyPath:
    """Test the happy path for project base URI retrieval."""

    def test_returns_s3_uri(self, event_builder, lambda_context):
        """Handler should return the S3 URI for the given project."""
        _mock_storage_config.get_s3_key_prefix_by_project_id.return_value = (
            "s3://project-data-bucket/byob-icav2/project-wgs/"
        )

        event = event_builder({"projectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4"})

        result = handler(event, lambda_context())

        assert result == {"s3Uri": "s3://project-data-bucket/byob-icav2/project-wgs/"}

    def test_calls_wrapica_with_project_id(self, event_builder, lambda_context):
        """Should call get_s3_key_prefix_by_project_id with the correct project ID."""
        _mock_storage_config.get_s3_key_prefix_by_project_id.return_value = "s3://bucket/prefix/"

        event = event_builder({"projectId": "test-project-id-123"})

        handler(event, lambda_context())

        _mock_storage_config.get_s3_key_prefix_by_project_id.assert_called_once_with(
            "test-project-id-123"
        )

    def test_sets_icav2_env_vars(self, event_builder, lambda_context):
        """Should call set_icav2_env_vars before making the API call."""
        _mock_storage_config.get_s3_key_prefix_by_project_id.return_value = "s3://bucket/prefix/"

        event = event_builder({"projectId": "proj-456"})

        handler(event, lambda_context())

        _mock_icav2_tools.set_icav2_env_vars.assert_called_once()


@pytest.mark.lambda_unit
class TestGetProjectBaseUriErrors:
    """Test error handling."""

    def test_missing_project_id_raises(self, event_builder, lambda_context):
        """Missing projectId should raise ValueError."""
        event = event_builder({})

        with pytest.raises(ValueError, match="projectId is a required input"):
            handler(event, lambda_context())

    def test_none_project_id_raises(self, event_builder, lambda_context):
        """None projectId should raise ValueError."""
        event = event_builder({"projectId": None})

        with pytest.raises(ValueError, match="projectId is a required input"):
            handler(event, lambda_context())
