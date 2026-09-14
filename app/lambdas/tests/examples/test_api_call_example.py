"""
Example: Testing a Lambda that Makes External API Calls
========================================================

This template demonstrates how to test a Lambda function that calls
external services (e.g., OrcaBus Metadata API, ICAv2 API). The key
technique is patching the external dependency at the module level
so the handler's logic can be tested in isolation.

Pattern:
    - Patch external API calls (e.g., orcabus_api_tools functions)
    - Provide controlled return values for each mocked call
    - Assert the handler correctly processes and transforms API responses
    - Test error handling when external calls fail

Real-world example: get_libraries_py
    - Calls orcabus_api_tools.metadata.get_library_from_library_orcabus_id()
    - Processes library metadata to extract phenotype and readset info
    - Returns structured output based on tumor/normal classification

Fixtures used:
    - event_builder: Wraps a dict payload into a Lambda event
    - lambda_context: Provides a mock Lambda context object

Note: For Lambdas that call AWS services directly (boto3), prefer
using the moto-based fixtures (mock_ssm_client, mock_s3_client, etc.)
instead of patching. See test_validation_example.py for that pattern.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup
#
# The get_libraries Lambda depends on the `orcabus_api_tools` layer package
# which is not installed in the local test environment. We mock the layer
# module before importing the handler so the import succeeds.
# This is the standard pattern for testing Lambdas that use Lambda Layers.
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[2] / "get_libraries_py"

# Mock the Lambda Layer dependency before importing the handler
_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_metadata = ModuleType("orcabus_api_tools.metadata")
_mock_metadata.get_library_from_library_orcabus_id = MagicMock()
_mock_api_tools.metadata = _mock_metadata

# The models module exports TypedDict types used for type hints.
# We provide plain dict as a stand-in since TypedDicts are just dicts at runtime.
_mock_models = ModuleType("orcabus_api_tools.metadata.models")
_mock_models.LibraryBase = dict
_mock_models.Library = dict
_mock_metadata.models = _mock_models

sys.modules.setdefault("orcabus_api_tools", _mock_api_tools)
sys.modules.setdefault("orcabus_api_tools.metadata", _mock_metadata)
sys.modules.setdefault("orcabus_api_tools.metadata.models", _mock_models)

sys.path.insert(0, str(LAMBDA_DIR))

from get_libraries import handler  # noqa: E402


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------


def make_library_with_readsets(library_id: str, orcabus_id: str, rgids: list[str]):
    """Create a library dict with readsets as it appears in the Lambda event."""
    return {
        "libraryId": library_id,
        "orcabusId": orcabus_id,
        "readsets": [
            {"orcabusId": f"rs.{rgid}", "rgid": rgid}
            for rgid in rgids
        ],
    }


def make_library_metadata(library_id: str, phenotype: str):
    """Create a library metadata dict as returned by the OrcaBus Metadata API."""
    return {
        "libraryId": library_id,
        "phenotype": phenotype,
        "type": "WGS",
        "assay": "TsqNano",
        "workflow": "research",
    }


# ---------------------------------------------------------------------------
# Tests: Single library (germline) — no API call needed
# ---------------------------------------------------------------------------


class TestSingleLibraryNoApiCall:
    """When only one library is provided, no external API call is made."""

    def test_single_library_returns_library_id_and_rgids(
        self, event_builder, lambda_context
    ):
        """A single library returns its ID and FASTQ readgroup IDs directly."""
        event = event_builder({
            "libraries": [
                make_library_with_readsets(
                    library_id="L2401001",
                    orcabus_id="lib.abc123",
                    rgids=["RGID001", "RGID002"],
                )
            ]
        })
        ctx = lambda_context(function_name="get-libraries")

        result = handler(event, ctx)

        assert result["libraryId"] == "L2401001"
        assert result["fastqRgidList"] == ["RGID001", "RGID002"]
        # Should NOT have tumor fields
        assert "tumorLibraryId" not in result

    def test_single_library_no_readsets_returns_empty_list(
        self, event_builder, lambda_context
    ):
        """A library with no readsets returns an empty RGID list."""
        event = event_builder({
            "libraries": [{
                "libraryId": "L2401001",
                "orcabusId": "lib.abc123",
                "readsets": None,
            }]
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result["libraryId"] == "L2401001"
        assert result["fastqRgidList"] == []


# ---------------------------------------------------------------------------
# Tests: Two libraries (tumor/normal pair) — requires API call
# ---------------------------------------------------------------------------


class TestTumorNormalPairWithMockedApi:
    """When two libraries are provided, the handler calls the Metadata API
    to determine which is tumor and which is normal."""

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_tumor_normal_pair_classified_correctly(
        self, mock_get_library, event_builder, lambda_context
    ):
        """Two libraries are correctly classified by phenotype via API lookup."""
        # Arrange: Mock the API to return phenotype metadata
        mock_get_library.side_effect = [
            make_library_metadata("L2401001", "tumor"),
            make_library_metadata("L2401002", "normal"),
        ]

        event = event_builder({
            "libraries": [
                make_library_with_readsets("L2401001", "lib.tumor1", ["RGID_T1"]),
                make_library_with_readsets("L2401002", "lib.normal1", ["RGID_N1", "RGID_N2"]),
            ]
        })
        ctx = lambda_context()

        # Act
        result = handler(event, ctx)

        # Assert: Normal library is primary, tumor is secondary
        assert result["libraryId"] == "L2401002"
        assert result["tumorLibraryId"] == "L2401001"
        assert result["fastqRgidList"] == ["RGID_N1", "RGID_N2"]
        assert result["tumorFastqRgidList"] == ["RGID_T1"]

        # Verify the API was called for each library
        assert mock_get_library.call_count == 2

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_missing_tumor_raises_error(
        self, mock_get_library, event_builder, lambda_context
    ):
        """If no tumor library is found in the pair, raise ValueError."""
        # Both return 'normal' phenotype — no tumor found
        mock_get_library.side_effect = [
            make_library_metadata("L2401001", "normal"),
            make_library_metadata("L2401002", "normal"),
        ]

        event = event_builder({
            "libraries": [
                make_library_with_readsets("L2401001", "lib.abc1", ["RGID1"]),
                make_library_with_readsets("L2401002", "lib.abc2", ["RGID2"]),
            ]
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="No tumor library found"):
            handler(event, ctx)

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_missing_normal_raises_error(
        self, mock_get_library, event_builder, lambda_context
    ):
        """If no normal library is found in the pair, raise ValueError."""
        # Both return 'tumor' phenotype — no normal found
        mock_get_library.side_effect = [
            make_library_metadata("L2401001", "tumor"),
            make_library_metadata("L2401002", "tumor"),
        ]

        event = event_builder({
            "libraries": [
                make_library_with_readsets("L2401001", "lib.abc1", ["RGID1"]),
                make_library_with_readsets("L2401002", "lib.abc2", ["RGID2"]),
            ]
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="No normal library found"):
            handler(event, ctx)


# ---------------------------------------------------------------------------
# Tests: Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Test handler behaviour with invalid inputs."""

    def test_empty_libraries_raises_error(self, event_builder, lambda_context):
        """An empty libraries list raises ValueError."""
        event = event_builder({"libraries": []})
        ctx = lambda_context()

        with pytest.raises(ValueError, match="No libraries provided"):
            handler(event, ctx)

    def test_too_many_libraries_raises_error(self, event_builder, lambda_context):
        """More than two libraries raises ValueError."""
        event = event_builder({
            "libraries": [
                make_library_with_readsets(f"L240100{i}", f"lib.abc{i}", [f"RGID{i}"])
                for i in range(3)
            ]
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="at most two libraries"):
            handler(event, ctx)
