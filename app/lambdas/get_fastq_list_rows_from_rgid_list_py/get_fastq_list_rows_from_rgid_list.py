#!/usr/bin/env python3

"""
Get the fastq list rows from the rgid list

Input is fastqRgidList

Output is fastqListRows (list)
"""

# Standard imports
from urllib.parse import urlparse
from pathlib import Path
from os import environ

# Layer imports
from orcabus_api_tools.fastq import to_fastq_list_row, get_fastq_by_rgid

# Globals
TEST_DATA_BUCKET_NAME_ENV_VAR = "TEST_DATA_BUCKET_NAME"


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

    # Test-data will have its own prefix
    fastq_list_rows = list(map(
        to_fastq_list_row,
        all_fastq_ids
    ))

    # Keep the test-data fastq list rows
    # (which are exempt from the requirement of being in a particular project prefix)
    non_test_data_fastq_list_ids = []
    test_data_fastq_list_rows = []
    for fastq_id_iter, fastq_list_row_iter in zip(all_fastq_ids, fastq_list_rows):
        if not fastq_list_row_iter['read1FileUri'].startswith(f"s3://{environ[TEST_DATA_BUCKET_NAME_ENV_VAR]}/"):
            non_test_data_fastq_list_ids.append(fastq_id_iter)
        else:
            test_data_fastq_list_rows.append(fastq_list_row_iter)

    # Re-collect the test-data fastq list rows with the s3 uri prefix if provided
    non_test_data_fastq_list_rows = list(map(
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
        non_test_data_fastq_list_ids
    ))

    return {
        "fastqListRows": test_data_fastq_list_rows + non_test_data_fastq_list_rows
    }
