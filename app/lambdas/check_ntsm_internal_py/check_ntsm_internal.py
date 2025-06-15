#!/usr/bin/env python3

"""
Check ntsm internal.

Given a list of rgids, collect all fastq set ids.

For each fastq set id in the list, run validateNtsmInternal.

If there is more than one fastq set id in the list, run validateNtsmExternal on each fastq set id.
"""

from itertools import product

from orcabus_api_tools.fastq import (
    validate_ntsm_internal,
    validate_ntsm_external, get_fastqs_in_instrument_run_id
)
from orcabus_api_tools.fastq.models import FastqListRow


def non_duplicate_cross_product(lst):
    result = []
    for a, b in product(lst, repeat=2):
        if a != b and (b, a) not in result:
            result.append((a, b))
    return result


def get_rgid_from_fastq_obj(fastq_obj: FastqListRow):
    return ".".join([
        fastq_obj['index'],
        str(fastq_obj['lane']),
        fastq_obj['instrumentRunId']
    ])


def handler(event, context):
    """
    Get fastq set ids from rgids and then validate ntsm internal.
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

    if len(all_fastq_set_ids_filtered) == 0:
        return {
            "related": None
        }

    if len(all_fastq_set_ids_filtered) == 1:
        return {
            "related": validate_ntsm_internal(all_fastq_set_ids_filtered[0])
        }

    return {
        # If any pair of fastq set ids fails validation, the result is False
        "related": all(list(map(
            lambda fastq_set_id_pair_iter_: validate_ntsm_external(
                fastq_set_id_pair_iter_[0], fastq_set_id_pair_iter_[1]
            ),
            non_duplicate_cross_product(all_fastq_set_ids_filtered)
        )))
    }


# Test
# if __name__ == "__main__":
#     import json
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "fastqRgidList": [
#                     "TGACGAAT+GCCTACTG.4.241024_A00130_0336_BHW7MVDSXC",
#                     "AAGTCCAA+TACTCATA.2.241024_A00130_0336_BHW7MVDSXC"
#                 ]
#             },
#             None
#         ),
#         indent=4
#     ))
