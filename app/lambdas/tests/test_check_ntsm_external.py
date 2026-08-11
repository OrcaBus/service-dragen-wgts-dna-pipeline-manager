"""Tests for check_ntsm_external Lambda function.

This Lambda validates that tumor and normal FASTQ sets are from related samples
by running external NTSM (nearest-truth sample matching) checks across all
cross-products of their FASTQ set IDs.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "check_ntsm_external_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_by_rgid = MagicMock()
_mock_fastq.validate_ntsm_external = MagicMock()
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq

sys.path.insert(0, str(LAMBDA_DIR))

from check_ntsm_external import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_by_rgid.reset_mock()
    _mock_fastq.validate_ntsm_external.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestCheckNtsmExternalPassing:
    """Test cases where all cross-product validations pass."""

    def test_single_pair_passing(self, event_builder, lambda_context):
        """A single normal/tumor pair that passes NTSM returns related=True."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-normal-1"},   # normal rgid
            {"fastqSetId": "fqs-tumor-1"},    # tumor rgid
        ]
        _mock_fastq.validate_ntsm_external.return_value = True

        event = event_builder({
            "fastqRgidList": ["NORMAL_RGID.1.RUN001"],
            "tumorFastqRgidList": ["TUMOR_RGID.1.RUN001"],
        })

        result = handler(event, lambda_context())

        assert result == {"related": True}
        _mock_fastq.validate_ntsm_external.assert_called_once_with(
            fastq_set_id="fqs-normal-1",
            external_fastq_set_id="fqs-tumor-1",
        )

    def test_multiple_pairs_all_passing(self, event_builder, lambda_context):
        """Multiple normal and tumor FASTQ sets all passing returns related=True."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-normal-1"},
            {"fastqSetId": "fqs-normal-2"},
            {"fastqSetId": "fqs-tumor-1"},
            {"fastqSetId": "fqs-tumor-2"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = True

        event = event_builder({
            "fastqRgidList": ["N_RGID.1.RUN001", "N_RGID.2.RUN001"],
            "tumorFastqRgidList": ["T_RGID.1.RUN001", "T_RGID.2.RUN001"],
        })

        result = handler(event, lambda_context())

        assert result == {"related": True}
        # Cross product of 2 normal x 2 tumor = 4 calls
        assert _mock_fastq.validate_ntsm_external.call_count == 4


@pytest.mark.lambda_unit
class TestCheckNtsmExternalFailing:
    """Test cases where NTSM validation fails."""

    def test_single_pair_failing(self, event_builder, lambda_context):
        """A single pair that fails NTSM returns related=False."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-normal-1"},
            {"fastqSetId": "fqs-tumor-1"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = False

        event = event_builder({
            "fastqRgidList": ["NORMAL_RGID.1.RUN001"],
            "tumorFastqRgidList": ["TUMOR_RGID.1.RUN001"],
        })

        result = handler(event, lambda_context())

        assert result == {"related": False}

    def test_one_pair_failing_in_cross_product(self, event_builder, lambda_context):
        """If any pair in the cross-product fails, result is related=False."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-normal-1"},
            {"fastqSetId": "fqs-tumor-1"},
            {"fastqSetId": "fqs-tumor-2"},
        ]
        # First cross-product passes, second fails
        _mock_fastq.validate_ntsm_external.side_effect = [True, False]

        event = event_builder({
            "fastqRgidList": ["N_RGID.1.RUN001"],
            "tumorFastqRgidList": ["T_RGID.1.RUN001", "T_RGID.2.RUN001"],
        })

        result = handler(event, lambda_context())

        assert result == {"related": False}


@pytest.mark.lambda_unit
class TestCheckNtsmExternalDeduplication:
    """Test that duplicate FASTQ set IDs are deduplicated."""

    def test_duplicate_rgids_same_fastq_set(self, event_builder, lambda_context):
        """Multiple RGIDs mapping to the same FASTQ set should be deduplicated."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-normal-1"},   # Both normal RGIDs map to same set
            {"fastqSetId": "fqs-normal-1"},
            {"fastqSetId": "fqs-tumor-1"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = True

        event = event_builder({
            "fastqRgidList": ["N_RGID.1.RUN001", "N_RGID.2.RUN001"],
            "tumorFastqRgidList": ["T_RGID.1.RUN001"],
        })

        result = handler(event, lambda_context())

        assert result == {"related": True}
        # Only 1 unique normal set x 1 tumor set = 1 call
        _mock_fastq.validate_ntsm_external.assert_called_once()
