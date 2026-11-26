"""Tests for get_fastq_rgids_from_library_id Lambda function.

This Lambda retrieves FASTQ RGIDs for a given library ID by looking up the
current FASTQ set and extracting RGIDs from the individual FASTQ objects.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_fastq_rgids_from_library_id_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_sets = MagicMock()
_mock_fastq.get_fastq_list_rows_in_fastq_set = MagicMock()
_mock_fastq_models = ModuleType("orcabus_api_tools.fastq.models")
_mock_fastq_models.Fastq = dict
_mock_fastq.models = _mock_fastq_models
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq
sys.modules["orcabus_api_tools.fastq.models"] = _mock_fastq_models

sys.path.insert(0, str(LAMBDA_DIR))

from get_fastq_rgids_from_library_id import handler, get_rgid_from_fastq_obj  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_sets.reset_mock()
    _mock_fastq.get_fastq_list_rows_in_fastq_set.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestGetFastqRgidsHappyPath:
    """Test the happy path for RGID retrieval."""

    def test_single_lane_library(self, event_builder, lambda_context):
        """A library with one lane should return one RGID."""
        _mock_fastq.get_fastq_sets.return_value = [{"id": "fqset-001"}]
        _mock_fastq.get_fastq_list_rows_in_fastq_set.return_value = [
            {"index": "AAGTCCAA+TACTCATA", "lane": 2, "instrumentRunId": "241024_A00130_0336_BHW7MVDSXC"}
        ]

        event = event_builder({"libraryId": "L2401541"})

        result = handler(event, lambda_context())

        assert result == {
            "fastqRgidList": ["AAGTCCAA+TACTCATA.2.241024_A00130_0336_BHW7MVDSXC"]
        }

    def test_multi_lane_library(self, event_builder, lambda_context):
        """A library with multiple lanes should return multiple RGIDs."""
        _mock_fastq.get_fastq_sets.return_value = [{"id": "fqset-002"}]
        _mock_fastq.get_fastq_list_rows_in_fastq_set.return_value = [
            {"index": "CAAGCTAG+CGCTATGT", "lane": 2, "instrumentRunId": "241024_A00130_0336_BHW7MVDSXC"},
            {"index": "CAAGCTAG+CGCTATGT", "lane": 3, "instrumentRunId": "241024_A00130_0336_BHW7MVDSXC"},
        ]

        event = event_builder({"libraryId": "L2401544"})

        result = handler(event, lambda_context())

        assert result == {
            "fastqRgidList": [
                "CAAGCTAG+CGCTATGT.2.241024_A00130_0336_BHW7MVDSXC",
                "CAAGCTAG+CGCTATGT.3.241024_A00130_0336_BHW7MVDSXC",
            ]
        }

    def test_fastq_sets_called_with_library_id(self, event_builder, lambda_context):
        """get_fastq_sets should be called with the correct library and currentFastqSet=True."""
        _mock_fastq.get_fastq_sets.return_value = [{"id": "fqset-001"}]
        _mock_fastq.get_fastq_list_rows_in_fastq_set.return_value = []

        event = event_builder({"libraryId": "L2401541"})

        handler(event, lambda_context())

        _mock_fastq.get_fastq_sets.assert_called_once_with(
            library="L2401541",
            currentFastqSet=True,
        )


@pytest.mark.lambda_unit
class TestGetFastqRgidsErrors:
    """Test error handling."""

    def test_no_fastq_set_found(self, event_builder, lambda_context):
        """If no FASTQ set is found, should raise ValueError."""
        _mock_fastq.get_fastq_sets.return_value = []

        event = event_builder({"libraryId": "L_MISSING"})

        with pytest.raises(ValueError, match="Expected exactly one current fastq set"):
            handler(event, lambda_context())

    def test_multiple_fastq_sets_found(self, event_builder, lambda_context):
        """If multiple FASTQ sets are found, should raise ValueError."""
        _mock_fastq.get_fastq_sets.return_value = [{"id": "fqset-001"}, {"id": "fqset-002"}]

        event = event_builder({"libraryId": "L_MULTI"})

        with pytest.raises(ValueError, match="Expected exactly one current fastq set"):
            handler(event, lambda_context())


@pytest.mark.lambda_unit
class TestGetRgidFromFastqObj:
    """Test the get_rgid_from_fastq_obj utility function."""

    def test_standard_format(self):
        """Should join index, lane, and instrumentRunId with dots."""
        fastq_obj = {
            "index": "AACTGAGG+AACTGAGG",
            "lane": 1,
            "instrumentRunId": "231010_A00130_0123_ABCDEFGHIJ",
        }

        result = get_rgid_from_fastq_obj(fastq_obj)

        assert result == "AACTGAGG+AACTGAGG.1.231010_A00130_0123_ABCDEFGHIJ"
