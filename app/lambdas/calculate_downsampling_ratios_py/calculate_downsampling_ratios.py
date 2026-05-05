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

If the ratio is greater than 3 or less than 1, we need to add in a
downsampler.
"""
from typing import Optional, Dict, Union

MAX_RATIO = 3
MIN_RATIO = 1


def handler(event, context) -> Optional[Dict[str, Union[float, bool]]]:
    """
    Run lambda handler
    """
    # Get inputs
    normal_coverage_estimate = event["normalCoverageEst"]
    tumor_coverage_estimate = event["tumorCoverageEst"]
    normal_dup_frac_estimate = event["normalDupFracEst"]
    tumor_dup_frac_estimate = event["tumorDupFracEst"]

    # Calculate the ratio
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
