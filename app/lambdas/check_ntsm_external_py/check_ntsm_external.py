#!/usr/bin/env python3

"""
Given a fastqRgidList and a tumorFastqRgidList
Collect the fastq set ids for each.

Then run the validateExternalNtsm script on each fastq set id for each tumor fastq set id.

We expect all fastq set ids to match all tumor fastq set ids.

"""
from itertools import product

from orcabus_api_tools.fastq import (
    get_fastq_by_rgid,
    validate_ntsm_external
)

def get_fastq_set_ids_from_rgid_list(fastq_rgid_list):

    # Remove any None values
    all_fastq_set_ids = list(map(
        lambda rgid_iter_: get_fastq_by_rgid(rgid_iter_)['fastqSetId'],
        fastq_rgid_list
    ))

    # Remove duplicates
    return sorted(set(all_fastq_set_ids))


def handler(event, context):
    """
    Part 1 - Get the fastq set ids for each fastqRgidList and tumorFastqRgidList.
    Part 2 - Generate a cross product of the fastq set ids and tumor fastq set ids.
    Part 3 - Run the validateExternalNtsm script on each fastq set id for each tumor fastq set id.
    :param event:
    :param context:
    :return:
    """

    # Get fastq rgid lists from the event
    fastq_rgid_ids = event.get('fastqRgidList', [])
    tumor_fastq_rgid_ids = event.get('tumorFastqRgidList', [])

    # Validate input
    fastq_set_ids = get_fastq_set_ids_from_rgid_list(fastq_rgid_ids)
    tumor_set_ids = get_fastq_set_ids_from_rgid_list(tumor_fastq_rgid_ids)

    # Generate cross product of fastq set ids and tumor fastq set ids
    return {
        "related": all(list(map(
            lambda fastq_set_id_pair_iter_: validate_ntsm_external(
                fastq_set_id=fastq_set_id_pair_iter_[0],
                external_fastq_set_id=fastq_set_id_pair_iter_[1]
            ),
            product(fastq_set_ids, tumor_set_ids)
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
#                     "TGACGAAT+GCCTACTG.4.241024_A00130_0336_BHW7MVDSXC"
#                 ],
#                 "tumorFastqRgidList": [
#                     "AAGTCCAA+TACTCATA.2.241024_A00130_0336_BHW7MVDSXC"
#                 ]
#             },
#             None
#         ),
#         indent=4
#     ))
