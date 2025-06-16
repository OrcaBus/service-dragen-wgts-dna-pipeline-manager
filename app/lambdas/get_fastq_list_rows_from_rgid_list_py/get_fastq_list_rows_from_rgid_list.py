#!/usr/bin/env python3

"""
Get the fastq list rows from the rgid list

Input is fastqRgidList

Output is fastqListRows
"""

from orcabus_api_tools.fastq import get_fastqs_in_instrument_run_id, to_fastq_list_row
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

    all_fastq_list_row_ids_filtered = []
    for fastq_iter_ in all_fastqs:
        if get_rgid_from_fastq_obj(fastq_iter_) in fastq_rgid_list:
            all_fastq_list_row_ids_filtered.append(fastq_iter_['id'])

    return {
        "fastqListRows": list(map(
            lambda fastq_id_iter_: to_fastq_list_row(fastq_id_iter_),
            all_fastq_list_row_ids_filtered
        ))
    }
