"""Tests for add_post_analysis_tags Lambda function.

This Lambda collects post-analysis QC metrics from S3 output files (CSVs, JSON)
and returns them as camelCase tags. It uses orcabus_api_tools.filemanager for
S3 file access, which we mock here.
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock the orcabus_api_tools layer and pandas dependency
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "add_post_analysis_tags_py"

_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_filemanager = ModuleType("orcabus_api_tools.filemanager")
_mock_filemanager.get_presigned_url = MagicMock()
_mock_filemanager.get_file_object_from_s3_uri = MagicMock()
_mock_filemanager_errors = ModuleType("orcabus_api_tools.filemanager.errors")
_mock_filemanager_errors.S3FileNotFoundError = type("S3FileNotFoundError", (Exception,), {})
_mock_filemanager.errors = _mock_filemanager_errors
_mock_api_tools.filemanager = _mock_filemanager

sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.filemanager"] = _mock_filemanager
sys.modules["orcabus_api_tools.filemanager.errors"] = _mock_filemanager_errors

sys.path.insert(0, str(LAMBDA_DIR))

from add_post_analysis_tags import handler, snake_to_camel  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset filemanager mocks between tests."""
    _mock_filemanager.get_presigned_url.reset_mock()
    _mock_filemanager.get_file_object_from_s3_uri.reset_mock()
    yield


# ---------------------------------------------------------------------------
# Tests: snake_to_camel utility
# ---------------------------------------------------------------------------


@pytest.mark.lambda_unit
class TestSnakeToCamel:
    """Test the snake_to_camel utility function."""

    def test_single_word(self):
        assert snake_to_camel("hello") == "hello"

    def test_two_words(self):
        assert snake_to_camel("hello_world") == "helloWorld"

    def test_multi_word(self):
        assert snake_to_camel("avg_autosomal_coverage_over_genome") == "avgAutosomalCoverageOverGenome"

    def test_with_tumor_prefix(self):
        assert snake_to_camel("tumor_hrd_score") == "tumorHrdScore"


# ---------------------------------------------------------------------------
# Tests: Handler with mocked S3 reads
# ---------------------------------------------------------------------------


@pytest.mark.lambda_unit
class TestAddPostAnalysisTagsNormal:
    """Test tags returned for a normal (non-tumor) sample."""

    @patch("add_post_analysis_tags.read_json_from_s3")
    @patch("add_post_analysis_tags.read_csv_from_s3")
    def test_normal_sample_returns_expected_keys(
        self, mock_read_csv, mock_read_json, event_builder, lambda_context
    ):
        """A normal sample should return coverage, contamination, dup, variants, tiTv."""
        import pandas as pd

        # Mock coverage CSV
        mock_read_csv.return_value = pd.DataFrame([
            {"summary": "COVERAGE SUMMARY", "region": "", "metric": "Average autosomal coverage over genome", "value": 82.16, "pct": None}
        ])

        # Mock metrics JSON
        mock_read_json.return_value = {
            "modules": {
                "mapAlign": {
                    "globalMetrics": {
                        "estimatedSampleContamination": {"value": 0.001},
                        "duplicateMarkedReads": {"percentage": 12.5},
                    }
                },
                "variantCaller": {
                    "postFilter": {
                        "SAMPLE001": {
                            "totalVariants": {"value": 4500000},
                            "tiTvRatio": {"value": 2.05},
                        }
                    }
                },
            }
        }

        event = event_builder({
            "variantCallingSampleName": "SAMPLE001",
            "variantCallingOutputUri": "s3://bucket/output/",
            "isTumor": False,
        })

        result = handler(event, lambda_context())

        assert "tags" in result
        tags = result["tags"]
        # Normal sample should NOT have tumor-specific keys
        assert "tumorHrdScore" not in tags
        assert "tumorTmbScore" not in tags
        # Should have these keys
        assert "avgAutosomalCoverageOverGenome" in tags
        assert "contaminationRate" in tags
        assert "duplicationFrac" in tags
        assert "totalPostFilterVariants" in tags
        assert "tiTvRatio" in tags

    @patch("add_post_analysis_tags.read_json_from_s3")
    @patch("add_post_analysis_tags.read_csv_from_s3")
    def test_none_values_are_dropped(
        self, mock_read_csv, mock_read_json, event_builder, lambda_context
    ):
        """Tags with None values should be excluded from the output."""
        mock_read_csv.return_value = None
        mock_read_json.return_value = None

        event = event_builder({
            "variantCallingSampleName": "SAMPLE001",
            "variantCallingOutputUri": "s3://bucket/output/",
            "isTumor": False,
        })

        result = handler(event, lambda_context())

        assert result == {"tags": {}}


@pytest.mark.lambda_unit
class TestAddPostAnalysisTagsTumor:
    """Test tags returned for a tumor sample."""

    @patch("add_post_analysis_tags.read_json_from_s3")
    @patch("add_post_analysis_tags.read_csv_from_s3")
    def test_tumor_sample_keys_prefixed(
        self, mock_read_csv, mock_read_json, event_builder, lambda_context
    ):
        """Tumor sample tags should be prefixed with 'tumor' in camelCase."""
        import pandas as pd

        # Each call to read_csv returns a different DF based on which file is read
        def csv_side_effect(uri, **kwargs):
            if "hrdscore" in uri:
                return pd.DataFrame([{"Sample": "TUMOR001", "HRD_Score": 45}])
            if "tmb.metrics" in uri:
                return pd.DataFrame([{"summary": "s", "null": None, "metric": "TMB", "value": 8.5}])
            if "sv_metrics" in uri:
                return pd.DataFrame([{
                    "summary": "SV SUMMARY", "sample": "TUMOR001",
                    "metric": "Total number of structural variants (PASS)", "value": 753, "pct": None
                }])
            if "cnv_metrics" in uri:
                return pd.DataFrame([
                    {"summary": "CNV SUMMARY", "sample": "", "metric": "Estimated tumor purity", "value": 0.60, "pct": None},
                    {"summary": "CNV SUMMARY", "sample": "", "metric": "Overall ploidy", "value": 2.06, "pct": None},
                ])
            if "wgs_coverage_metrics_tumor" in uri:
                return pd.DataFrame([{
                    "summary": "COVERAGE SUMMARY", "region": "", "metric": "Average autosomal coverage over genome",
                    "value": 74.43, "pct": None
                }])
            return None

        mock_read_csv.side_effect = csv_side_effect

        mock_read_json.return_value = {
            "modules": {
                "mapAlign": {
                    "globalMetrics": {
                        "estimatedSampleContamination": {"value": 0.002},
                        "duplicateMarkedReads": {"percentage": 14.39},
                    }
                },
                "variantCaller": {
                    "postFilter": {
                        "TUMOR001": {
                            "totalVariants": {"value": 55000},
                            "tiTvRatio": {"value": 1.8},
                        }
                    }
                },
            }
        }

        event = event_builder({
            "variantCallingSampleName": "TUMOR001",
            "variantCallingOutputUri": "s3://bucket/output/",
            "isTumor": True,
        })

        result = handler(event, lambda_context())

        tags = result["tags"]
        # Tumor keys should be prefixed
        assert "tumorHrdScore" in tags
        assert tags["tumorHrdScore"] == 45
        assert "tumorTmbScore" in tags
        assert "tumorSvPassCount" in tags
        assert "tumorCnvEstimatedTumorPurity" in tags
        assert "tumorCnvOverallPloidy" in tags
        assert "tumorAvgAutosomalCoverageOverGenome" in tags
        assert "tumorContaminationRate" in tags
        assert "tumorDuplicationFrac" in tags


@pytest.mark.lambda_unit
class TestAddPostAnalysisTagsInputValidation:
    """Test error handling for missing inputs."""

    def test_missing_sample_name_raises(self, event_builder, lambda_context):
        """Missing variantCallingSampleName should raise ValueError."""
        event = event_builder({
            "variantCallingOutputUri": "s3://bucket/output/",
        })

        with pytest.raises(ValueError, match="Missing required inputs"):
            handler(event, lambda_context())

    def test_missing_output_uri_raises(self, event_builder, lambda_context):
        """Missing variantCallingOutputUri should raise ValueError."""
        event = event_builder({
            "variantCallingSampleName": "SAMPLE001",
        })

        with pytest.raises(ValueError, match="Missing required inputs"):
            handler(event, lambda_context())
