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
    validate_ntsm_external,
    get_fastq_by_rgid
)


def non_duplicate_cross_product(lst):
    result = []
    for a, b in product(lst, repeat=2):
        if a != b and (b, a) not in result:
            result.append((a, b))
    return result


def handler(event, context):
    """
    Get fastq set ids from rgids and then validate ntsm internal.
    :param event:
    :param context:
    :return:
    """
    fastq_rgid_list = event.get("fastqRgidList", [])

    fastq_set_id_list = list(map(
        lambda rgid_iter_: get_fastq_by_rgid(rgid_iter_)['fastqSetId'],
        fastq_rgid_list
    ))

    if len(fastq_set_id_list) == 0:
        return {
            "related": None
        }

    if len(fastq_set_id_list) == 1:
        return {
            "related": validate_ntsm_internal(fastq_set_id_list[0])
        }

    return {
        # If any pair of fastq set ids fails validation, the result is False
        "related": all(list(map(
            lambda fastq_set_id_pair_iter_: validate_ntsm_external(
                fastq_set_id_pair_iter_[0], fastq_set_id_pair_iter_[1]
            ),
            non_duplicate_cross_product(fastq_set_id_list)
        )))
    }


# Test
# if __name__ == "__main__":
#     import json
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "fastqRgidList": [
#                     "GTTCGCCG+CAATGAGC.4.250724_A01052_0269_AHFHWJDSXF"
#                 ]
#             },
#             None
#         ),
#         indent=4
#     ))
