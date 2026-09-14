"""Tests for check_ntsm_internal Lambda function.

This Lambda validates that all FASTQ sets within a list of RGIDs are from the
same sample, using internal and cross-set NTSM validation.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "check_ntsm_internal_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_by_rgid = MagicMock()
_mock_fastq.validate_ntsm_internal = MagicMock()
_mock_fastq.validate_ntsm_external = MagicMock()
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq

sys.path.insert(0, str(LAMBDA_DIR))

from check_ntsm_internal import handler, non_duplicate_cross_product  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_by_rgid.reset_mock()
    _mock_fastq.validate_ntsm_internal.reset_mock()
    _mock_fastq.validate_ntsm_external.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestCheckNtsmInternalEmptyInput:
    """Test behaviour with empty RGID list."""

    def test_empty_list_returns_none(self, event_builder, lambda_context):
        """An empty RGID list should return related=None."""
        event = event_builder({"fastqRgidList": []})

        result = handler(event, lambda_context())

        assert result == {"related": None}


@pytest.mark.lambda_unit
class TestCheckNtsmInternalSingleSet:
    """Test behaviour with a single FASTQ set (internal validation only)."""

    def test_single_rgid_passing(self, event_builder, lambda_context):
        """A single RGID that passes internal NTSM returns related=True."""
        _mock_fastq.get_fastq_by_rgid.return_value = {"fastqSetId": "fqs-001"}
        _mock_fastq.validate_ntsm_internal.return_value = True

        event = event_builder({"fastqRgidList": ["RGID.1.RUN001"]})

        result = handler(event, lambda_context())

        assert result == {"related": True}
        _mock_fastq.validate_ntsm_internal.assert_called_once_with("fqs-001")

    def test_single_rgid_failing(self, event_builder, lambda_context):
        """A single RGID that fails internal NTSM returns related=False."""
        _mock_fastq.get_fastq_by_rgid.return_value = {"fastqSetId": "fqs-001"}
        _mock_fastq.validate_ntsm_internal.return_value = False

        event = event_builder({"fastqRgidList": ["RGID.1.RUN001"]})

        result = handler(event, lambda_context())

        assert result == {"related": False}


@pytest.mark.lambda_unit
class TestCheckNtsmInternalMultipleSets:
    """Test behaviour with multiple FASTQ sets (external cross-validation)."""

    def test_two_sets_both_passing(self, event_builder, lambda_context):
        """Two distinct FASTQ sets that pass external NTSM return related=True."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-001"},
            {"fastqSetId": "fqs-002"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = True

        event = event_builder({"fastqRgidList": ["RGID.1.RUN001", "RGID.2.RUN001"]})

        result = handler(event, lambda_context())

        assert result == {"related": True}
        # Non-duplicate cross product of 2 items = 1 pair
        _mock_fastq.validate_ntsm_external.assert_called_once_with("fqs-001", "fqs-002")

    def test_two_sets_one_failing(self, event_builder, lambda_context):
        """If external NTSM fails between any pair, result is related=False."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-001"},
            {"fastqSetId": "fqs-002"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = False

        event = event_builder({"fastqRgidList": ["RGID.1.RUN001", "RGID.2.RUN001"]})

        result = handler(event, lambda_context())

        assert result == {"related": False}

    def test_three_sets_all_passing(self, event_builder, lambda_context):
        """Three distinct FASTQ sets with all cross pairs passing return related=True."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"fastqSetId": "fqs-001"},
            {"fastqSetId": "fqs-002"},
            {"fastqSetId": "fqs-003"},
        ]
        _mock_fastq.validate_ntsm_external.return_value = True

        event = event_builder({"fastqRgidList": ["RGID.1.R", "RGID.2.R", "RGID.3.R"]})

        result = handler(event, lambda_context())

        assert result == {"related": True}
        # Non-duplicate cross product of 3 = 3 pairs
        assert _mock_fastq.validate_ntsm_external.call_count == 3


@pytest.mark.lambda_unit
class TestNonDuplicateCrossProduct:
    """Test the non_duplicate_cross_product utility function."""

    def test_two_items(self):
        """Two items should produce one pair."""
        result = non_duplicate_cross_product(["a", "b"])
        assert result == [("a", "b")]

    def test_three_items(self):
        """Three items should produce three pairs (no duplicates or reverses)."""
        result = non_duplicate_cross_product(["a", "b", "c"])
        assert len(result) == 3
        assert ("a", "b") in result
        assert ("a", "c") in result
        assert ("b", "c") in result

    def test_single_item(self):
        """A single item should produce no pairs."""
        result = non_duplicate_cross_product(["a"])
        assert result == []

    def test_empty_list(self):
        """An empty list should produce no pairs."""
        result = non_duplicate_cross_product([])
        assert result == []
