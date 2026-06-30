#!/usr/bin/env python3

"""
Generate a WorkflowRunUpdate event object with merged data.

This Lambda constructs the complete WRU event detail object from the current state
of the draft population process.
"""

from orcabus_api_tools.workflow import get_workflow_run_from_portal_run_id


def handler(event, context):
    """
    Generate WRU event object with merged data for the dragen-wgts-dna pipeline.

    Input:
    {
        "portalRunId": "...",
        "libraries": [...],
        "payload": {
            "version": "...",
            "data": {
                "inputs": {...},
                "tags": {...},
                "engineParameters": {...}
            }
        }
    }

    Output:
    {
        "workflowRunUpdate": {
            "orcabusId": "...",
            "portalRunId": "...",
            "status": "DRAFT",
            "workflow": {...},
            "libraries": [...],
            "payload": {...}
        }
    }
    """
    portal_run_id = event["portalRunId"]
    libraries = event.get("libraries", [])
    payload = event.get("payload", {})

    # Get the current workflow run object from the API
    workflow_run = get_workflow_run_from_portal_run_id(portal_run_id=portal_run_id)

    # Build the workflow run update object
    workflow_run_update = {
        "orcabusId": workflow_run["orcabusId"],
        "portalRunId": workflow_run["portalRunId"],
        "status": "DRAFT",
        "workflow": workflow_run["workflow"],
        "workflowRunName": workflow_run["workflowRunName"],
        "linkedLibraries": workflow_run.get("linkedLibraries", []),
        "libraries": list(map(
            lambda lib: {
                "libraryId": lib["libraryId"],
                "orcabusId": lib["orcabusId"],
                "readsets": lib.get("readsets", []),
            },
            libraries
        )),
        "payload": payload,
    }

    return {"workflowRunUpdate": workflow_run_update}
