#!/usr/bin/env python3

"""
Calculate downsampling ratios

Inputs are

* normalCoverageEst
* normalDupFracEst
* tumorCoverageEst
* tumorDupFracEst

Ensure that
(tumorCoverageEst * (1 - tumorDupFracEst)) /
(normalCoverageEst * (1 - normalDupFracEst))

stays between 1 and 3 inclusive.

If the ratio is greater than 3 we subsample the tumor down to 3,
if the ratio is less than 1 we subsample the normal down to the tumor level.
"""
from typing import Optional, Dict, Union

MAX_RATIO = 3
MIN_RATIO = 1


def _validate_inputs(
    normal_coverage_estimate: float,
    tumor_coverage_estimate: float,
    normal_dup_frac_estimate: float,
    tumor_dup_frac_estimate: float,
) -> None:
    """
    Validate that coverage estimates and duplication fractions are within
    acceptable ranges before computing the tumor/normal ratio.

    Raises ValueError if any value is out of range.
    """
    # Coverage estimates must be positive (negative values such as -1 indicate
    # that QC stats were unavailable)
    if normal_coverage_estimate <= 0:
        raise ValueError(
            f"normalCoverageEst must be > 0, got {normal_coverage_estimate}"
        )
    if tumor_coverage_estimate <= 0:
        raise ValueError(
            f"tumorCoverageEst must be > 0, got {tumor_coverage_estimate}"
        )

    # Duplication fractions must be in [0, 1).  A value of 1 would make the
    # effective coverage zero and cause a ZeroDivisionError; negative values
    # are nonsensical.
    if not (0 <= normal_dup_frac_estimate < 1):
        raise ValueError(
            f"normalDupFracEst must be in [0, 1), got {normal_dup_frac_estimate}"
        )
    if not (0 <= tumor_dup_frac_estimate < 1):
        raise ValueError(
            f"tumorDupFracEst must be in [0, 1), got {tumor_dup_frac_estimate}"
        )


def handler(event, context) -> Optional[Dict[str, Union[float, bool]]]:
    """
    Run lambda handler
    """
    # Get inputs
    normal_coverage_estimate = event["normalCoverageEst"]
    tumor_coverage_estimate = event["tumorCoverageEst"]
    normal_dup_frac_estimate = event["normalDupFracEst"]
    tumor_dup_frac_estimate = event["tumorDupFracEst"]

    # Validate inputs before computing the ratio
    _validate_inputs(
        normal_coverage_estimate,
        tumor_coverage_estimate,
        normal_dup_frac_estimate,
        tumor_dup_frac_estimate,
    )

    # Calculate the effective coverage ratio (tumor / normal)
    ratio = (
            (
                tumor_coverage_estimate * (1 - tumor_dup_frac_estimate)
            ) /
            (
                normal_coverage_estimate * (1 - normal_dup_frac_estimate)
            )
    )

    # If the ratio is greater than 3
    # Then we subsample the tumor down to 3
    if ratio > MAX_RATIO:
        return {
            "enableFractionalDownSampler": True,
            "downSamplerTumorSubsample": round(MAX_RATIO / ratio, 2)
        }
    elif ratio < MIN_RATIO:
        return {
            "enableFractionalDownSampler": True,
            "downSamplerNormalSubsample": round(ratio / MIN_RATIO, 2)
        }

    # Otherwise return none
    return None
