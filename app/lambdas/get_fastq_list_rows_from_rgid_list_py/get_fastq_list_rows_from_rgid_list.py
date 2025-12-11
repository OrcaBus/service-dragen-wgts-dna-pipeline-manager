#!/usr/bin/env python3

"""
Get the fastq list rows from the rgid list

Input is fastqRgidList

Output is fastqListRows (list)
"""

# Standard imports
from urllib.parse import urlparse
from pathlib import Path

# Layer imports
from orcabus_api_tools.fastq import to_fastq_list_row, get_fastq_by_rgid


def handler(event, context):
    """
    Given a list of rgids, return the fastq list rows
    :param event:
    :param context:
    :return:
    """

    # Get the input parameters
    fastq_rgid_list = event.get("fastqRgidList", [])
    s3_uri_prefix = event.get("s3UriPrefix", None)

    # Convert the uri prefix to a parsed object
    s3_uri_obj = (
        urlparse(s3_uri_prefix)
        if s3_uri_prefix is not None
        else None
    )

    # Collect all fastq ids from the rgid list
    all_fastq_ids = sorted(list(map(
        lambda fastq_rgid_iter_: get_fastq_by_rgid(fastq_rgid_iter_)['id'],
        fastq_rgid_list
    )))

    return {
        "fastqListRows": list(map(
            lambda fastq_id_iter_: to_fastq_list_row(
                fastq_id_iter_,
                **(
                    {
                        "bucket": s3_uri_obj.netloc,
                        "key_prefix": (str(Path(s3_uri_obj.path)) + "/").lstrip('/')
                    }
                    if s3_uri_obj is not None
                    else {}
                )
            ),
            all_fastq_ids
        ))
    }
