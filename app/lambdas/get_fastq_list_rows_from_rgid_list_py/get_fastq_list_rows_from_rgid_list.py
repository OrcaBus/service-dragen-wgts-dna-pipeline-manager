#!/usr/bin/env python3

"""
Get the fastq list rows from the rgid list

Input is fastqRgidList

Output is fastqListRows (list)
"""

from orcabus_api_tools.fastq import to_fastq_list_row, get_fastq_by_rgid


def handler(event, context):
    """
    Given a list of rgids, return the fastq list rows
    :param event:
    :param context:
    :return:
    """
    fastq_rgid_list = event.get("fastqRgidList", [])

    all_fastq_ids = sorted(list(map(
        lambda fastq_rgid_iter_: get_fastq_by_rgid(fastq_rgid_iter_)['id'],
        fastq_rgid_list
    )))

    return {
        "fastqListRows": list(map(
            lambda fastq_id_iter_: to_fastq_list_row(fastq_id_iter_),
            all_fastq_ids
        ))
    }
