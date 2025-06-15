#!/usr/bin/env python3

"""
Get the fastq set ids from the rgid list

Given the rgid list, return the fastq set ids that are associated with these rgids.
"""

from orcabus_api_tools.fastq import get_fastqs_in_instrument_run_id, get_fastq_list_rows_in_fastq_set
from orcabus_api_tools.fastq.models import FastqListRow, BoolAllEnum

def get_rgid_from_fastq_obj(fastq_obj: FastqListRow):
    return ".".join([
        fastq_obj['index'],
        str(fastq_obj['lane']),
        fastq_obj['instrumentRunId']
    ])


def handler(event, context):
    """
    Given a library id, get the fastq rgids associated with the library.
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

    all_fastq_set_ids_filtered = []
    for fastq_iter_ in all_fastqs:
        if get_rgid_from_fastq_obj(fastq_iter_) in fastq_rgid_list:
            all_fastq_set_ids_filtered.append(fastq_iter_.get('fastqSetId', None))

    # Remove any None values
    all_fastq_set_ids_filtered = list(filter(
        lambda fastq_set_id_iter_: fastq_set_id_iter_ is not None,
        all_fastq_set_ids_filtered
    ))

    # Remove duplicates
    all_fastq_set_ids_filtered = sorted(list(set(all_fastq_set_ids_filtered)))

    return {
        "fastqSetIdList": all_fastq_set_ids_filtered
    }
