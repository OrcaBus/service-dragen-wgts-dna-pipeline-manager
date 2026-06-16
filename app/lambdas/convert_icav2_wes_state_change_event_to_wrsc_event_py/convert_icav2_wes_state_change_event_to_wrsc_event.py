#!/usr/bin/env python3

"""
Convert ICAv2 WES State Change Event to WRSC Event

Given an ICAv2 WES State Change Event, this script converts it to a WRSC Event.

{
  "id": "iwa.01JWAGE5PWS5JN48VWNPYSTJRN",
  "name": "umccr--automated--bclconvert-interop-qc--2024-05-24--20250417abcd1234",
  "inputs": {
    "bclconvert_report_directory": {
      "class": "Directory",
      "location": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/20231010_pi1-07_0329_A222N7LTD3/202504179cac7411/Reports/"
    },
    "interop_directory": {
      "class": "Directory",
      "location": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/20231010_pi1-07_0329_A222N7LTD3/202504179cac7411/InterOp/"
    },
    "instrument_run_id": "20231010_pi1-07_0329_A222N7LTD3"
  },
  "engineParameters": {
    "pipelineId": "55a8bb47-d32b-48dd-9eac-373fd487ccec",
    "projectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4",
    "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/bclconvert-interop-qc-test/",
    "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/logs/bclconvert-interop-qc-test/"
  },
  "tags": {
    "instrumentRunId": "20231010_pi1-07_0329_A222N7LTD3",
    "portalRunId": "20250417abcd1234"  // pragma: allowlist secret
  },
  "status": "SUBMITTED",
  "submissionTime": "2025-05-28T03:54:35.612655",
  "stepsLaunchExecutionArn": "arn:aws:states:ap-southeast-2:843407916570:execution:icav2-wes-launchIcav2Analysis:3f176fc2-d8e0-4bd5-8d2f-f625d16f6bf6",
  "icav2AnalysisId": null,
  "startTime": "2025-05-28T03:54:35.662401+00:00",
  "endTime": null
}

TO

{
  // Workflow run status
  "status": "RUNNING",
  // Timestamp of the event
  "timestamp": "2025-04-22T00:09:07.220Z",
  // Portal Run ID For the BSSH Fastq Copy Manager
  "portalRunId": "20250417abcd1234",  // pragma: allowlist secret
  // Workflow name
  "workflowName": "bclconvert-interop-qc",
  // Workflow version
  "workflowVersion": "2025.05.24",
  // Workflow run name
  "workflowRunName": "umccr--automated--bclconvert-interop-qc--2024-05-24--20250417abcd1234",
  // Linked libraries in the instrument run
  "linkedLibraries": [
    {
      "orcabusId": "lib.12345",
      "libraryId": "L20202020"
    }
  ],
  "payload": {
    "refId": "workflowmanagerrefid",
    "version": "2024.07.01",
    "data": {
      // Original inputs from READY State
      "inputs": {
        // The instrument run ID is used to identify the BCLConvert InterOp QC Manager workflow
        // We get this from the BSSH Fastq To AWS S3 Copy Succeeded Event payload.data.inputs.instrumentRunId
        "instrumentRunId": "20231010_pi1-07_0329_A222N7LTD3",
        // InterOp Directory
        // Collected from the payload.data.outputs.outputUri + 'InterOp/'
        "interOpDirectory": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/20231010_pi1-07_0329_A222N7LTD3/202504179cac7411/InterOp/",
        // BCLConvert Report Directory
        // Collected from the payload.data.outputs.outputUri + 'Reports/'
        "bclConvertReportDirectory": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/20231010_pi1-07_0329_A222N7LTD3/202504179cac7411/Reports/"
      },
      // The engine parameters are used to launch the BCLConvert InterOp QC Manager workflow on ICAv2
      "engineParameters": {
        // The output URI is used to identify the BCLConvert InterOp QC Manager workflow
        "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/analysis/bclconvert-interop-qc/20250417abcd1234/",
        // This is where the ICA Logs will be stored
        "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/logs/bclconvert-interop-qc/20250417abcd1234/",
        // The ICAv2 Project ID we use to launch the workflow
        "projectId": "uuid4",
        // Pipeline Id
        "pipelineId": "uuid4",
        // ICAv2 Analysis Id
        "analysisId": "uuid4",
        // The ICAv2 WES Analysis OrcaBus ID
        "icav2WesAnalysisOrcaBusId": "iwa.01JWAGE5PWS5JN48VWNPYSTJRN"
      },
      // Tags (same as bssh fastq to aws s3 copy succeeded event)
      "tags": {
       "instrumentRunId": "20231010_pi1-07_0329_A222N7LTD3"
      }
    }
  }
}
"""
# Standard imports
from copy import deepcopy
from datetime import datetime, timezone

# Layer helpers
from orcabus_api_tools.workflow import (
    get_latest_payload_from_workflow_run,
    get_workflow_run_from_portal_run_id
)


def handler(event, context):
    """
    Perform the following steps:
    1. Get portal run ID from ICAv2 WES Event Tags
    2. Look up workflow run / payload using the portal run ID
    3. Generate the WRSC Event payload based on the existing WRSC Event payload
    :param event:
    :param context:
    :return:
    """

    # ICAV2 WES State Change Event payload
    icav2_wes_event = event['icav2WesStateChangeEvent']

    # Get the portal run ID from the event tags
    portal_run_id = icav2_wes_event['tags']['portalRunId']
    execution_id = icav2_wes_event.get('icav2AnalysisId')

    # Get the workflow run using the portal run ID
    workflow_run = get_workflow_run_from_portal_run_id(portal_run_id)

    # Add the execution id to the payload if it doesn't exist
    if execution_id and not workflow_run.get("executionId"):
        workflow_run['executionId'] = execution_id

    # Get the latest payload from the workflow run
    latest_payload = get_latest_payload_from_workflow_run(workflow_run['orcabusId'])

    # Check if the status was SUCCEEDED, if so we populate the 'outputs' data payload
    if icav2_wes_event['status'] == 'SUCCEEDED':
        # Get the inputs from the latest payload
        inputs = latest_payload['data']['inputs']

        germline_variant_calling_output_rel_path = "__".join([
            inputs['sampleName'],
            inputs['reference']['name'],
            inputs['reference']['structure'],
            "dragen_wgts_dna_germline_variant_calling"
        ]) + "/"

        # Set somatic outputs to None by default
        somatic_variant_calling_output_rel_path = None

        # Add multiqc report details
        # These will change if tumor sample name is provided
        multiqc_output_rel_path = f"{inputs['sampleName']}_multiqc/"

        # Check if the somatic variant calling is enabled
        if inputs.get('tumorSampleName', None) is not None:
            # Get the tumor reference
            if inputs.get('somaticReference', None) is not None:
                somatic_reference = inputs['somaticReference']
            else:
                somatic_reference = inputs['reference']
            somatic_variant_calling_output_rel_path = "__".join([
                inputs['tumorSampleName'],
                inputs['sampleName'],
                somatic_reference['name'],
                somatic_reference['structure'],
                "dragen_wgts_dna_somatic_variant_calling"
            ]) + "/"

            # Now redefine the multiqc report details
            multiqc_output_rel_path = f"{inputs['tumorSampleName']}__{inputs['sampleName']}__multiqc/"

        outputs = dict(filter(
            lambda kv_iter_: kv_iter_[1] is not None,
            {
                'dragenGermlineVariantCallingOutputRelPath': germline_variant_calling_output_rel_path,
                'dragenSomaticVariantCallingOutputRelPath': somatic_variant_calling_output_rel_path,
                'multiQcOutputRelPath': multiqc_output_rel_path,
            }.items()
        ))
    else:
        outputs = None

    # Check if the status was FAILED, if so we populate the error message and type
    if icav2_wes_event['status'] == 'FAILED':
        error_type = icav2_wes_event.get('errorType', 'UnknownErrorType')
        error_message_uri = icav2_wes_event.get('errorMessageUri', None)
    else:
        error_message_uri = None
        error_type = None

    # Update the latest payload with the outputs if available
    if outputs:
        latest_payload['data']['outputs'] = outputs

    # Update the workflow object to contain 'name' and 'version'
    workflow = dict(deepcopy(workflow_run['workflow']))
    if 'workflowName' in workflow:
        workflow['name'] = workflow.pop('workflowName')
    if 'workflowVersion' in workflow:
        workflow['version'] = workflow.pop('workflowVersion')

    # Prepare the WRSC Event payload
    return {
        "workflowRunStateChangeEvent": {
            # New status
            "status": icav2_wes_event['status'],
            # Current time
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds').replace("+00:00", "Z"),
            # Portal Run ID
            "portalRunId": portal_run_id,
            # Workflow details
            "workflow": workflow,
            "workflowRunName": workflow_run['workflowRunName'],
            # Linked libraries in workflow run
            "libraries": workflow_run['libraries'],
            # Payload containing the original inputs and engine parameters
            # But with the updated outputs if available
            "payload": {
                "version": latest_payload['version'],
                "data": latest_payload['data']
            },
            # Optional values
            **dict(filter(
                lambda kv_iter_: kv_iter_[1] is not None,
                {
                    "executionId": execution_id,
                }.items()
            ))
        },
        "errorMessageUri": error_message_uri,
        "errorType": error_type,
    }
