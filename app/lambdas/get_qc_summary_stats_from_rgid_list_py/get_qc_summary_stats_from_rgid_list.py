#!/usr/bin/env python3

"""
Given a list of rgids, collect the fastq list row object for each rgid.

Then sum the qc coverage estimates and
average out the duplication fraction estimates
and average out the insert size estimates.
"""
from typing import List

from orcabus_api_tools.fastq import get_fastqs_in_instrument_run_id
from orcabus_api_tools.fastq.models import FastqListRow


def get_rgid_from_fastq_obj(fastq_obj: FastqListRow):
    return ".".join([
        fastq_obj['index'],
        str(fastq_obj['lane']),
        fastq_obj['instrumentRunId']
    ])


def handler(event, context):
    """
    Given a list of rgids, return the fastq list rows
    :param event:
    :param context:
    :return:
    """
    fastq_rgid_list = event.get("fastqRgidList", [])

    instrument_run_id_list = sorted(set(list(map(
        lambda rgid_iter_: rgid_iter_.rsplit(".", 1)[-1],
        fastq_rgid_list
    ))))

    all_fastqs = []
    for instrument_run_id_iter_ in instrument_run_id_list:
        all_fastqs = get_fastqs_in_instrument_run_id(instrument_run_id_iter_)

    all_fastq_list_rows_filtered: List[FastqListRow] = []
    for fastq_iter_ in all_fastqs:
        if get_rgid_from_fastq_obj(fastq_iter_) in fastq_rgid_list:
            all_fastq_list_rows_filtered.append(fastq_iter_)

    # Collect and return the qc coverage estimates
    return {
        "coverageSum": round(
            (
                sum(list(map(
                    lambda fastq_iter_: fastq_iter_['qc']['rawWgsCoverageEstimate'],
                    all_fastq_list_rows_filtered
                )))
            ) if all_fastq_list_rows_filtered else -1,
            2
        ),
        "dupFracAvg": round(
            (
                    sum(list(map(
                        lambda fastq_iter_: fastq_iter_['qc']['duplicationFractionEstimate'],
                        all_fastq_list_rows_filtered
                    ))) / len(all_fastq_list_rows_filtered)
            ) if all_fastq_list_rows_filtered else -1,
            2
        ),
        "insertSizeAvg": round(
            (
                    sum(list(map(
                        lambda fastq_iter_: fastq_iter_['qc']['insertSizeEstimate'],
                        all_fastq_list_rows_filtered
                    ))) / len(all_fastq_list_rows_filtered)
            ) if all_fastq_list_rows_filtered else -1,
            2
        )
    }
