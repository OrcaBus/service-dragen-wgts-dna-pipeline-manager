"""
Example: Testing a Pure Data Transformation Lambda
===================================================

This template demonstrates how to test a Lambda function that performs
pure input/output transformations — no external service calls, no AWS SDK
usage. These are the simplest Lambdas to test because they are
deterministic functions of their inputs.

Pattern:
    - Call handler(event, context) with known inputs
    - Assert the output matches expected values
    - Test edge cases (boundary values, empty inputs, invalid inputs)

Real-world example: calculate_downsampling_ratios_py
    - Takes coverage and duplication estimates
    - Returns downsampling ratios based on business logic
    - No AWS API calls — pure computation

Fixtures used:
    - event_builder: Wraps a dict payload into a Lambda event
    - lambda_context: Provides a mock Lambda context object
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup: add the Lambda source directory to sys.path so the handler
# can be imported directly without packaging.
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[2] / "calculate_downsampling_ratios_py"
sys.path.insert(0, str(LAMBDA_DIR))

from calculate_downsampling_ratios import handler  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDataTransformationHappyPath:
    """Test the happy path where the ratio falls within acceptable bounds."""

    def test_ratio_within_bounds_returns_none(self, event_builder, lambda_context):
        """When the tumor/normal ratio is between 1 and 3, no downsampling is needed."""
        # Arrange: Set coverage so ratio = 2.0 (within [1, 3])
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 60.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context(function_name="calculate-downsampling-ratios")

        # Act
        result = handler(event, ctx)

        # Assert: No downsampling needed
        assert result is None

    def test_ratio_exactly_one_returns_none(self, event_builder, lambda_context):
        """Boundary: ratio exactly 1.0 should not trigger downsampling."""
        event = event_builder({
            "normalCoverageEst": 50.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.1,
            "tumorDupFracEst": 0.1,
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result is None

    def test_ratio_exactly_three_returns_none(self, event_builder, lambda_context):
        """Boundary: ratio exactly 3.0 should not trigger downsampling."""
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 90.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result is None


class TestDataTransformationDownsampling:
    """Test cases where downsampling IS required."""

    def test_high_ratio_downsamples_tumor(self, event_builder, lambda_context):
        """When ratio > 3, tumor should be downsampled."""
        # ratio = 6.0 (> MAX_RATIO of 3)
        event = event_builder({
            "normalCoverageEst": 30.0,
            "tumorCoverageEst": 180.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result is not None
        assert result["enableFractionalDownSampler"] is True
        assert "downSamplerTumorSubsample" in result
        # 3/6 = 0.5
        assert result["downSamplerTumorSubsample"] == 0.5

    def test_low_ratio_downsamples_normal(self, event_builder, lambda_context):
        """When ratio < 1, normal should be downsampled."""
        # ratio = 0.5 (< MIN_RATIO of 1)
        event = event_builder({
            "normalCoverageEst": 100.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        result = handler(event, ctx)

        assert result is not None
        assert result["enableFractionalDownSampler"] is True
        assert "downSamplerNormalSubsample" in result
        # 0.5 / 1 = 0.5
        assert result["downSamplerNormalSubsample"] == 0.5


class TestDataTransformationEdgeCases:
    """Test edge cases and invalid inputs."""

    def test_zero_normal_coverage_raises_error(self, event_builder, lambda_context):
        """Invalid input: zero coverage should raise ValueError."""
        event = event_builder({
            "normalCoverageEst": 0.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="normalCoverageEst must be > 0"):
            handler(event, ctx)

    def test_negative_coverage_raises_error(self, event_builder, lambda_context):
        """Invalid input: negative coverage (QC unavailable) should raise ValueError."""
        event = event_builder({
            "normalCoverageEst": -1.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 0.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="normalCoverageEst must be > 0"):
            handler(event, ctx)

    def test_dup_frac_one_raises_error(self, event_builder, lambda_context):
        """Invalid input: duplication fraction of 1.0 would cause division by zero."""
        event = event_builder({
            "normalCoverageEst": 50.0,
            "tumorCoverageEst": 50.0,
            "normalDupFracEst": 1.0,
            "tumorDupFracEst": 0.0,
        })
        ctx = lambda_context()

        with pytest.raises(ValueError, match="normalDupFracEst must be in"):
            handler(event, ctx)

    def test_missing_key_raises_key_error(self, event_builder, lambda_context):
        """Missing required input field raises KeyError."""
        event = event_builder({
            "normalCoverageEst": 50.0,
            # Missing tumorCoverageEst and other fields
        })
        ctx = lambda_context()

        with pytest.raises(KeyError):
            handler(event, ctx)
