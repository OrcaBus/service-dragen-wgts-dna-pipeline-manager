"""Tests for get_fastq_id_list_from_rgid_list Lambda function.

This Lambda converts a list of FASTQ RGIDs to their corresponding FASTQ IDs
by looking each one up via the orcabus_api_tools.fastq API.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_fastq_id_list_from_rgid_list_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_by_rgid = MagicMock()
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq

sys.path.insert(0, str(LAMBDA_DIR))

from get_fastq_id_list_from_rgid_list import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_by_rgid.reset_mock(side_effect=True, return_value=True)
    yield


@pytest.mark.lambda_unit
class TestGetFastqIdListHappyPath:
    """Test the happy path for RGID to FASTQ ID conversion."""

    def test_single_rgid(self, event_builder, lambda_context):
        """A single RGID should return a single FASTQ ID."""
        _mock_fastq.get_fastq_by_rgid.return_value = {
            "id": "fqr.01K12NF97VEM0V9K0ABFAEPHNT"
        }

        event = event_builder({
            "fastqRgidList": ["GTTCGCCG+CAATGAGC.4.250724_A01052_0269_AHFHWJDSXF"]
        })

        result = handler(event, lambda_context())

        assert result == {"fastqIdList": ["fqr.01K12NF97VEM0V9K0ABFAEPHNT"]}

    def test_multiple_rgids(self, event_builder, lambda_context):
        """Multiple RGIDs should return multiple sorted FASTQ IDs."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"id": "fqr.BBB"},
            {"id": "fqr.AAA"},
            {"id": "fqr.CCC"},
        ]

        event = event_builder({
            "fastqRgidList": ["RGID1.1.RUN", "RGID2.2.RUN", "RGID3.3.RUN"]
        })

        result = handler(event, lambda_context())

        # Results should be sorted
        assert result == {"fastqIdList": ["fqr.AAA", "fqr.BBB", "fqr.CCC"]}

    def test_empty_list(self, event_builder, lambda_context):
        """An empty RGID list should return an empty FASTQ ID list."""
        event = event_builder({"fastqRgidList": []})

        result = handler(event, lambda_context())

        assert result == {"fastqIdList": []}
        _mock_fastq.get_fastq_by_rgid.assert_not_called()

    def test_api_called_for_each_rgid(self, event_builder, lambda_context):
        """The API should be called once for each RGID in the input."""
        _mock_fastq.get_fastq_by_rgid.return_value = {"id": "fqr.TEST"}

        event = event_builder({
            "fastqRgidList": ["RGID1.1.RUN", "RGID2.2.RUN"]
        })

        handler(event, lambda_context())

        assert _mock_fastq.get_fastq_by_rgid.call_count == 2


@pytest.mark.lambda_unit
class TestGetFastqIdListMissingKey:
    """Test behaviour when fastqRgidList key is missing."""

    def test_missing_key_defaults_to_empty(self, event_builder, lambda_context):
        """Missing fastqRgidList should default to empty list."""
        event = event_builder({})

        result = handler(event, lambda_context())

        assert result == {"fastqIdList": []}
