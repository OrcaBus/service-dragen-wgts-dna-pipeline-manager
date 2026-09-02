"""Tests for get_metadata_tags Lambda function.

This Lambda retrieves library metadata from the OrcaBus Metadata API
given a library ID. It's a simple pass-through wrapper.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.metadata layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_metadata_tags_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_metadata = ModuleType("orcabus_api_tools.metadata")
_mock_metadata.get_library_from_library_id = MagicMock()
_mock_api_tools.metadata = _mock_metadata

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.metadata"] = _mock_metadata

sys.path.insert(0, str(LAMBDA_DIR))

from get_metadata_tags import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_metadata.get_library_from_library_id.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestGetMetadataTagsHappyPath:
    """Test the happy path for metadata tag retrieval."""

    def test_returns_library_obj(self, event_builder, lambda_context):
        """Handler should return the libraryObj from the API."""
        expected_lib = {
            "libraryId": "L2401001",
            "phenotype": "tumor",
            "type": "WGS",
            "assay": "TsqNano",
            "workflow": "clinical",
            "subject": {"subjectId": "SBJ001"},
        }
        _mock_metadata.get_library_from_library_id.return_value = expected_lib

        event = event_builder({"libraryId": "L2401001"})

        result = handler(event, lambda_context())

        assert result == {"libraryObj": expected_lib}

    def test_api_called_with_library_id(self, event_builder, lambda_context):
        """The API should be called with the provided library ID."""
        _mock_metadata.get_library_from_library_id.return_value = {"libraryId": "L2401002"}

        event = event_builder({"libraryId": "L2401002"})

        handler(event, lambda_context())

        _mock_metadata.get_library_from_library_id.assert_called_once_with("L2401002")

    def test_different_library_metadata(self, event_builder, lambda_context):
        """Should correctly return metadata for different library types."""
        expected_lib = {
            "libraryId": "L2401003",
            "phenotype": "normal",
            "type": "WGS",
            "assay": "TsqNano",
            "workflow": "research",
        }
        _mock_metadata.get_library_from_library_id.return_value = expected_lib

        event = event_builder({"libraryId": "L2401003"})

        result = handler(event, lambda_context())

        assert result["libraryObj"]["phenotype"] == "normal"
        assert result["libraryObj"]["workflow"] == "research"


@pytest.mark.lambda_unit
class TestGetMetadataTagsErrors:
    """Test error handling."""

    def test_missing_library_id_raises(self, event_builder, lambda_context):
        """Missing libraryId key should raise KeyError."""
        event = event_builder({})

        with pytest.raises(KeyError):
            handler(event, lambda_context())
