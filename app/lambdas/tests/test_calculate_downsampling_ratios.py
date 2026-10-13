"""Tests for calculate_downsampling_ratios Lambda function.

This Lambda computes downsampling ratios for tumor/normal pairs based on
estimated coverage and duplication fractions. It is a pure data transformation
with no external dependencies.
"""

import sys
from pathlib import Path

import pytest

# Path setup for Lambda handler import
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "calculate_downsampling_ratios_py"
sys.path.insert(0, str(LAMBDA_DIR))

from calculate_downsampling_ratios import handler  # noqa: E402


@pytest.mark.lambda_unit
class TestNoDownsamplingNeeded:
    """When the tumor/normal coverage ratio is within [1, 3], no downsampling."""

    def test_ratio_within_bounds(self, event_builder, lambda_context):
        """Ratio of 2.0 is within bounds — no downsampling needed."""
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 60.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        result = handler(event, lambda_context())

        assert result is None

    def test_ratio_exactly_one(self, event_builder, lambda_context):
        """Boundary: ratio = 1.0 should not trigger downsampling."""
        event = event_builder({
            "normalCoverageEst": 50.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.1,
            "tumorDupFracEst": 0.1,
        })
        result = handler(event, lambda_context())

        assert result is None

    def test_ratio_exactly_three(self, event_builder, lambda_context):
        """Boundary: ratio = 3.0 should not trigger downsampling."""
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 90.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        result = handler(event, lambda_context())

        assert result is None

    def test_with_duplication_adjustments(self, event_builder, lambda_context):
        """Ratio within bounds after accounting for duplication fractions."""
        # Effective coverage: normal = 40 * (1 - 0.2) = 32, tumor = 80 * (1 - 0.1) = 72
        # Ratio = 72 / 32 = 2.25 — within [1, 3]
        event = event_builder({
            "normalCoverageEst": 40.0,
            "tumorCoverageEst": 80.0,
            "normalDupFracEst": 0.2,
            "tumorDupFracEst": 0.1,
        })
        result = handler(event, lambda_context())

        assert result is None


@pytest.mark.lambda_unit
class TestTumorDownsampling:
    """When ratio > 3, the tumor should be downsampled."""

    def test_high_ratio_downsamples_tumor(self, event_builder, lambda_context):
        """Ratio = 6.0 (> MAX_RATIO of 3) should downsample tumor to 0.5."""
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 180.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        result = handler(event, lambda_context())

        assert result is not None
        assert result["enableFractionalDownSampler"] is True
        assert "downSamplerTumorSubsample" in result
        assert result["downSamplerTumorSubsample"] == pytest.approx(0.5)

    def test_moderate_high_ratio(self, event_builder, lambda_context):
        """Ratio = 4.0 (> 3) should downsample tumor to 0.75."""
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 120.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        result = handler(event, lambda_context())

        assert result is not None
        assert result["enableFractionalDownSampler"] is True
        assert result["downSamplerTumorSubsample"] == pytest.approx(0.75)


@pytest.mark.lambda_unit
class TestNormalDownsampling:
    """When ratio < 1, the normal should be downsampled."""

    def test_low_ratio_downsamples_normal(self, event_builder, lambda_context):
        """Ratio = 0.5 (< MIN_RATIO of 1) should downsample normal to 0.5."""
        event = event_builder({
            "normalCoverageEst": 100.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        result = handler(event, lambda_context())

        assert result is not None
        assert result["enableFractionalDownSampler"] is True
        assert "downSamplerNormalSubsample" in result
        assert result["downSamplerNormalSubsample"] == pytest.approx(0.5)


@pytest.mark.lambda_unit
class TestEdgeCases:
    """Test error handling for invalid inputs."""

    def test_zero_normal_coverage_raises_error(self, event_builder, lambda_context):
        """Zero coverage should raise ValueError."""
        event = event_builder({
            "normalCoverageEst": 0.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })

        with pytest.raises(ValueError, match="normalCoverageEst must be > 0"):
            handler(event, lambda_context())

    def test_negative_coverage_raises_error(self, event_builder, lambda_context):
        """Negative coverage should raise ValueError."""
        event = event_builder({
            "normalCoverageEst": -1.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })

        with pytest.raises(ValueError, match="normalCoverageEst must be > 0"):
            handler(event, lambda_context())

    def test_dup_frac_one_raises_error(self, event_builder, lambda_context):
        """Duplication fraction of 1.0 would cause division by zero."""
        event = event_builder({
            "normalCoverageEst": 50.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 1.0,
            "tumorDupFracEst": 0.0,
        })

        with pytest.raises(ValueError, match="normalDupFracEst must be in"):
            handler(event, lambda_context())

    def test_missing_key_raises_key_error(self, event_builder, lambda_context):
        """Missing required input field raises KeyError."""
        event = event_builder({"normalCoverageEst": 50.0})

        with pytest.raises(KeyError):
            handler(event, lambda_context())
