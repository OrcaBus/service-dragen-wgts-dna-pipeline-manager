#!/usr/bin/env python3

"""
Given a list of rgids, collect the fastq list row object for each rgid.

Then sum the qc coverage estimates and
average out the duplication fraction estimates
and average out the insert size estimates.
"""
from typing import List

from orcabus_api_tools.fastq import get_fastq_by_rgid
from orcabus_api_tools.fastq.models import Fastq


def handler(event, context):
    """
    Given a list of rgids, return the fastq list rows
    :param event:
    :param context:
    :return:
    """
    fastq_rgid_list = event.get("fastqRgidList", [])

    fastq_obj_list: List[Fastq] = list(map(
        lambda rgid_iter_: get_fastq_by_rgid(rgid_iter_),
        fastq_rgid_list
    ))


    # Collect and return the qc coverage estimates
    return {
        "coverageSum": round(
            (
                sum(list(map(
                    lambda fastq_iter_: fastq_iter_['qc']['rawWgsCoverageEstimate'],
                    fastq_obj_list
                )))
            ) if fastq_obj_list else -1,
            2
        ),
        "dupFracAvg": round(
            (
                    sum(list(map(
                        lambda fastq_iter_: fastq_iter_['qc']['duplicationFractionEstimate'],
                        fastq_obj_list
                    ))) / len(fastq_obj_list)
            ) if fastq_obj_list else -1,
            2
        ),
        "insertSizeAvg": round(
            (
                    sum(list(map(
                        lambda fastq_iter_: fastq_iter_['qc']['insertSizeEstimate'],
                        fastq_obj_list
                    ))) / len(fastq_obj_list)
            ) if fastq_obj_list else -1,
            2
        )
    }
