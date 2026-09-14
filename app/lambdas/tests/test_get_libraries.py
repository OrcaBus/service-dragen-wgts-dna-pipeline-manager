"""Tests for get_libraries Lambda function.

This Lambda classifies libraries as tumor/normal based on metadata API lookups
and returns structured output with library IDs and FASTQ RGIDs.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_libraries_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_metadata = ModuleType("orcabus_api_tools.metadata")
_mock_metadata.get_library_from_library_orcabus_id = MagicMock()
_mock_api_tools.metadata = _mock_metadata

_mock_models = ModuleType("orcabus_api_tools.metadata.models")
_mock_models.LibraryBase = dict
_mock_models.Library = dict
_mock_metadata.models = _mock_models

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.metadata"] = _mock_metadata
sys.modules["orcabus_api_tools.metadata.models"] = _mock_models

sys.path.insert(0, str(LAMBDA_DIR))

from get_libraries import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_metadata.get_library_from_library_orcabus_id.reset_mock()
    yield


def _make_library(library_id, orcabus_id, rgids):
    """Build a library dict with readsets."""
    return {
        "libraryId": library_id,
        "orcabusId": orcabus_id,
        "readsets": [{"orcabusId": f"rs.{rgid}", "rgid": rgid} for rgid in rgids],
    }


def _make_library_metadata(library_id, phenotype):
    """Build a library metadata dict as returned by the API."""
    return {
        "libraryId": library_id,
        "phenotype": phenotype,
        "type": "WGS",
        "assay": "TsqNano",
        "workflow": "research",
    }


@pytest.mark.lambda_unit
class TestSingleLibrary:
    """Test single library (germline) handling — no API call needed."""

    def test_single_library_returns_id_and_rgids(self, event_builder, lambda_context):
        """A single library returns its ID and FASTQ RGIDs."""
        event = event_builder({
            "libraries": [_make_library("L2401001", "lib.abc123", ["RGID001", "RGID002"])]
        })

        result = handler(event, lambda_context())

        assert result["libraryId"] == "L2401001"
        assert result["fastqRgidList"] == ["RGID001", "RGID002"]
        assert "tumorLibraryId" not in result

    def test_single_library_no_readsets(self, event_builder, lambda_context):
        """A library with None readsets returns an empty RGID list."""
        event = event_builder({
            "libraries": [{"libraryId": "L2401001", "orcabusId": "lib.abc", "readsets": None}]
        })

        result = handler(event, lambda_context())

        assert result["libraryId"] == "L2401001"
        assert result["fastqRgidList"] == []


@pytest.mark.lambda_unit
class TestTumorNormalPair:
    """Test tumor/normal pair handling — requires API lookup."""

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_correctly_classified(self, mock_get_lib, event_builder, lambda_context):
        """Two libraries are correctly classified by phenotype."""
        mock_get_lib.side_effect = [
            _make_library_metadata("L2401001", "tumor"),
            _make_library_metadata("L2401002", "normal"),
        ]

        event = event_builder({
            "libraries": [
                _make_library("L2401001", "lib.tumor1", ["RGID_T1"]),
                _make_library("L2401002", "lib.normal1", ["RGID_N1", "RGID_N2"]),
            ]
        })

        result = handler(event, lambda_context())

        assert result["libraryId"] == "L2401002"
        assert result["tumorLibraryId"] == "L2401001"
        assert result["fastqRgidList"] == ["RGID_N1", "RGID_N2"]
        assert result["tumorFastqRgidList"] == ["RGID_T1"]

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_no_tumor_raises(self, mock_get_lib, event_builder, lambda_context):
        """If no tumor library is found, raise ValueError."""
        mock_get_lib.side_effect = [
            _make_library_metadata("L2401001", "normal"),
            _make_library_metadata("L2401002", "normal"),
        ]

        event = event_builder({
            "libraries": [
                _make_library("L2401001", "lib.a", ["RG1"]),
                _make_library("L2401002", "lib.b", ["RG2"]),
            ]
        })

        with pytest.raises(ValueError, match="No tumor library found"):
            handler(event, lambda_context())

    @patch("get_libraries.get_library_from_library_orcabus_id")
    def test_no_normal_raises(self, mock_get_lib, event_builder, lambda_context):
        """If no normal library is found, raise ValueError."""
        mock_get_lib.side_effect = [
            _make_library_metadata("L2401001", "tumor"),
            _make_library_metadata("L2401002", "tumor"),
        ]

        event = event_builder({
            "libraries": [
                _make_library("L2401001", "lib.a", ["RG1"]),
                _make_library("L2401002", "lib.b", ["RG2"]),
            ]
        })

        with pytest.raises(ValueError, match="No normal library found"):
            handler(event, lambda_context())


@pytest.mark.lambda_unit
class TestInputValidation:
    """Test input validation."""

    def test_empty_libraries_raises(self, event_builder, lambda_context):
        """Empty libraries list raises ValueError."""
        event = event_builder({"libraries": []})

        with pytest.raises(ValueError, match="No libraries provided"):
            handler(event, lambda_context())

    def test_too_many_libraries_raises(self, event_builder, lambda_context):
        """More than two libraries raises ValueError."""
        event = event_builder({
            "libraries": [
                _make_library(f"L24010{i}", f"lib.{i}", [f"RG{i}"])
                for i in range(3)
            ]
        })

        with pytest.raises(ValueError, match="at most two libraries"):
            handler(event, lambda_context())
