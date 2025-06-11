#!/usr/bin/env python3

"""
Generate a workflow run name and portal run ID
"""

from orcabus_api_tools.workflow import (
    create_portal_run_id,
    create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id
)
from os import environ
from typing import Dict

def handler(event, context) -> Dict[str, str]:
    """
    Generate a workflow run name and portal run ID

    Need to get a few things from the environment
    """

    # Get the workflow name and version from the environment
    workflow_name = environ['WORKFLOW_NAME']
    workflow_version = environ['WORKFLOW_VERSION']

    # Get the portal run ID from the toolkit
    portal_run_id = create_portal_run_id()

    # Create the workflow run name
    workflow_run_name = create_workflow_run_name_from_workflow_name_workflow_version_and_portal_run_id(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        portal_run_id=portal_run_id
    )

    return {
        "portalRunId": portal_run_id,
        "workflowRunName": workflow_run_name,
    }


# if __name__ == "__main__":
#     import json
#     environ['WORKFLOW_NAME'] = 'example_workflow'
#     environ['WORKFLOW_VERSION'] = '1.0.0'
#     print(
#         json.dumps(
#             handler(
#                 event={},
#                 context=None
#             ),
#             indent=4
#         )
#     )
#
#     # {
#     #     "workflowRunName": "umccr--automated--example-workflow--1-0-0--202505295cf24ec1"
#     # }
