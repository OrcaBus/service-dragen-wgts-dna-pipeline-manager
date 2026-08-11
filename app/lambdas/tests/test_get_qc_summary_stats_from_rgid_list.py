"""Tests for get_qc_summary_stats_from_rgid_list Lambda function.

This Lambda collects QC summary stats (coverage, duplication fraction, insert size)
from FASTQ objects by RGID, then sums/averages them.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_qc_summary_stats_from_rgid_list_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_by_rgid = MagicMock()
_mock_fastq_models = ModuleType("orcabus_api_tools.fastq.models")
_mock_fastq_models.Fastq = dict
_mock_fastq.models = _mock_fastq_models
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq
sys.modules["orcabus_api_tools.fastq.models"] = _mock_fastq_models

sys.path.insert(0, str(LAMBDA_DIR))

from get_qc_summary_stats_from_rgid_list import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_by_rgid.reset_mock()
    yield


def _make_fastq_obj(coverage, dup_frac, insert_size):
    """Build a FASTQ object with QC stats."""
    return {
        "qc": {
            "rawWgsCoverageEstimate": coverage,
            "duplicationFractionEstimate": dup_frac,
            "insertSizeEstimate": insert_size,
        }
    }


@pytest.mark.lambda_unit
class TestGetQcSummaryStatsHappyPath:
    """Test the happy path for QC stat aggregation."""

    def test_single_rgid(self, event_builder, lambda_context):
        """A single RGID should return its stats directly."""
        _mock_fastq.get_fastq_by_rgid.return_value = _make_fastq_obj(30.5, 0.12, 350.0)

        event = event_builder({"fastqRgidList": ["RGID.1.RUN"]})

        result = handler(event, lambda_context())

        assert result["coverageSum"] == 30.5
        assert result["dupFracAvg"] == 0.12
        assert result["insertSizeAvg"] == 350.0

    def test_multiple_rgids_summed_and_averaged(self, event_builder, lambda_context):
        """Multiple RGIDs should sum coverage and average dup/insert."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            _make_fastq_obj(30.0, 0.10, 300.0),
            _make_fastq_obj(20.0, 0.20, 400.0),
        ]

        event = event_builder({"fastqRgidList": ["RGID.1.RUN", "RGID.2.RUN"]})

        result = handler(event, lambda_context())

        assert result["coverageSum"] == 50.0  # 30 + 20
        assert result["dupFracAvg"] == 0.15   # (0.10 + 0.20) / 2
        assert result["insertSizeAvg"] == 350.0  # (300 + 400) / 2

    def test_three_rgids(self, event_builder, lambda_context):
        """Three RGIDs should correctly sum and average."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            _make_fastq_obj(10.0, 0.10, 300.0),
            _make_fastq_obj(20.0, 0.20, 350.0),
            _make_fastq_obj(30.0, 0.30, 400.0),
        ]

        event = event_builder({"fastqRgidList": ["RG1.1.R", "RG2.2.R", "RG3.3.R"]})

        result = handler(event, lambda_context())

        assert result["coverageSum"] == 60.0  # 10 + 20 + 30
        assert result["dupFracAvg"] == 0.2    # (0.1 + 0.2 + 0.3) / 3
        assert result["insertSizeAvg"] == 350.0  # (300 + 350 + 400) / 3


@pytest.mark.lambda_unit
class TestGetQcSummaryStatsEmptyInput:
    """Test behaviour with empty RGID list."""

    def test_empty_list_returns_negative_one(self, event_builder, lambda_context):
        """An empty RGID list should return -1 for all stats."""
        event = event_builder({"fastqRgidList": []})

        result = handler(event, lambda_context())

        assert result["coverageSum"] == -1
        assert result["dupFracAvg"] == -1
        assert result["insertSizeAvg"] == -1


@pytest.mark.lambda_unit
class TestGetQcSummaryStatsRounding:
    """Test that results are rounded to 2 decimal places."""

    def test_values_rounded_to_2dp(self, event_builder, lambda_context):
        """Results should be rounded to 2 decimal places."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            _make_fastq_obj(10.123456, 0.123456, 333.333333),
            _make_fastq_obj(20.654321, 0.654321, 666.666666),
        ]

        event = event_builder({"fastqRgidList": ["RG1.1.R", "RG2.2.R"]})

        result = handler(event, lambda_context())

        assert result["coverageSum"] == 30.78  # round(30.777777, 2)
        assert result["dupFracAvg"] == 0.39    # round(0.388888, 2)
        assert result["insertSizeAvg"] == 500.0  # round(500.0, 2)
