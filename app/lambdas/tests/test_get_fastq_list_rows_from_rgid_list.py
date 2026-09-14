"""Tests for get_fastq_list_rows_from_rgid_list Lambda function.

This Lambda converts a list of RGIDs to FASTQ list rows (with file URIs),
handling test-data vs non-test-data buckets and optional S3 URI prefix overrides.
"""

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools.fastq layer and requests
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "get_fastq_list_rows_from_rgid_list_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_fastq = ModuleType("orcabus_api_tools.fastq")
_mock_fastq.get_fastq_by_rgid = MagicMock()
_mock_fastq.to_fastq_list_row = MagicMock()
_mock_api_tools.fastq = _mock_fastq

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.fastq"] = _mock_fastq

sys.path.insert(0, str(LAMBDA_DIR))

from get_fastq_list_rows_from_rgid_list import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _set_env_vars():
    """Set required environment variables."""
    with patch.dict(os.environ, {"TEST_DATA_BUCKET_NAME": "test-data-bucket"}):
        yield


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset mocks between tests."""
    _mock_fastq.get_fastq_by_rgid.reset_mock()
    _mock_fastq.to_fastq_list_row.reset_mock()
    yield


@pytest.mark.lambda_unit
class TestGetFastqListRowsHappyPath:
    """Test the happy path for converting RGIDs to FASTQ list rows."""

    @patch("get_fastq_list_rows_from_rgid_list.is_fastq_id_in_test_data_project")
    def test_single_rgid_non_test_data(self, mock_is_test, event_builder, lambda_context):
        """A single RGID not in test-data should use default bucket."""
        mock_is_test.return_value = False
        _mock_fastq.get_fastq_by_rgid.return_value = {"id": "fqr.001"}
        _mock_fastq.to_fastq_list_row.return_value = {
            "rgid": "RGID.1.RUN",
            "rgsm": "SMP001",
            "rglb": "L001",
            "lane": 1,
            "read1FileUri": "s3://bucket/r1.fastq.gz",
            "read2FileUri": "s3://bucket/r2.fastq.gz",
        }

        event = event_builder({"fastqRgidList": ["RGID.1.RUN"]})

        result = handler(event, lambda_context())

        assert "fastqListRows" in result
        assert len(result["fastqListRows"]) == 1
        assert result["fastqListRows"][0]["rgid"] == "RGID.1.RUN"

    @patch("get_fastq_list_rows_from_rgid_list.is_fastq_id_in_test_data_project")
    def test_single_rgid_test_data(self, mock_is_test, event_builder, lambda_context):
        """A single RGID in test-data should use the test bucket."""
        mock_is_test.return_value = True
        _mock_fastq.get_fastq_by_rgid.return_value = {"id": "fqr.001"}
        _mock_fastq.to_fastq_list_row.return_value = {
            "rgid": "RGID.1.RUN",
            "rgsm": "SMP001",
            "rglb": "L001",
            "lane": 1,
            "read1FileUri": "s3://test-data-bucket/r1.fastq.gz",
            "read2FileUri": "s3://test-data-bucket/r2.fastq.gz",
        }

        event = event_builder({"fastqRgidList": ["RGID.1.RUN"]})

        result = handler(event, lambda_context())

        assert len(result["fastqListRows"]) == 1
        # Verify test bucket was used
        _mock_fastq.to_fastq_list_row.assert_called_with(
            "fqr.001", bucket="test-data-bucket"
        )

    @patch("get_fastq_list_rows_from_rgid_list.is_fastq_id_in_test_data_project")
    def test_with_s3_uri_prefix(self, mock_is_test, event_builder, lambda_context):
        """A non-test RGID with s3UriPrefix should pass bucket and key_prefix."""
        mock_is_test.return_value = False
        _mock_fastq.get_fastq_by_rgid.return_value = {"id": "fqr.001"}
        _mock_fastq.to_fastq_list_row.return_value = {
            "rgid": "RGID.1.RUN",
            "rgsm": "SMP001",
            "rglb": "L001",
            "lane": 1,
            "read1FileUri": "s3://project-bucket/prefix/r1.fastq.gz",
            "read2FileUri": "s3://project-bucket/prefix/r2.fastq.gz",
        }

        event = event_builder({
            "fastqRgidList": ["RGID.1.RUN"],
            "s3UriPrefix": "s3://project-bucket/prefix/path",
        })

        result = handler(event, lambda_context())

        assert len(result["fastqListRows"]) == 1
        # Verify bucket and key_prefix were passed
        _mock_fastq.to_fastq_list_row.assert_called_with(
            "fqr.001",
            bucket="project-bucket",
            key_prefix="prefix/path/",
        )

    @patch("get_fastq_list_rows_from_rgid_list.is_fastq_id_in_test_data_project")
    def test_empty_list(self, mock_is_test, event_builder, lambda_context):
        """An empty RGID list should return an empty fastqListRows."""
        event = event_builder({"fastqRgidList": []})

        result = handler(event, lambda_context())

        assert result == {"fastqListRows": []}


@pytest.mark.lambda_unit
class TestGetFastqListRowsMixed:
    """Test mixed test-data and non-test-data RGIDs."""

    @patch("get_fastq_list_rows_from_rgid_list.is_fastq_id_in_test_data_project")
    def test_mixed_test_and_non_test(self, mock_is_test, event_builder, lambda_context):
        """A mix of test and non-test RGIDs should handle both correctly."""
        _mock_fastq.get_fastq_by_rgid.side_effect = [
            {"id": "fqr.test001"},
            {"id": "fqr.prod001"},
        ]
        # First RGID is test data, second is not
        mock_is_test.side_effect = [True, False]

        test_row = {"rgid": "TEST.1.RUN", "rgsm": "SMP_T", "rglb": "L_T", "lane": 1,
                    "read1FileUri": "s3://test-data-bucket/r1.fq", "read2FileUri": "s3://test-data-bucket/r2.fq"}
        prod_row = {"rgid": "PROD.1.RUN", "rgsm": "SMP_P", "rglb": "L_P", "lane": 1,
                    "read1FileUri": "s3://prod-bucket/r1.fq", "read2FileUri": "s3://prod-bucket/r2.fq"}

        _mock_fastq.to_fastq_list_row.side_effect = [test_row, prod_row]

        event = event_builder({"fastqRgidList": ["TEST.1.RUN", "PROD.1.RUN"]})

        result = handler(event, lambda_context())

        assert len(result["fastqListRows"]) == 2
