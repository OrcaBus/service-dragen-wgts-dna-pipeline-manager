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

    # Get the output URI from the engine parameters
    output_uri = icav2_wes_event['engineParameters']['outputUri']

    # Get the portal run ID from the event tags
    portal_run_id = icav2_wes_event['tags']['portalRunId']

    # Get the workflow run using the portal run ID
    workflow_run = get_workflow_run_from_portal_run_id(portal_run_id)

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
            "dragen_germline_variant_calling"
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
                "dragen_somatic_variant_calling"
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
            }
        }
    }


# if __name__ == "__main__":
#     import json
#     from os import environ
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "icav2WesStateChangeEvent": {
#                     "id": "iwa.01JY07DV46QMQJWH1J1Y8YFR27",
#                     "name": "umccr--automated--dragen-wgts-dna--4-4-4--20250617ac346b29",
#                     "inputs": {
#                         "alignment_options": {
#                             "enable_duplicate_marking": True
#                         },
#                         "targeted_caller_options": {
#                             "enable_targeted": [
#                                 "cyp2d6"
#                             ]
#                         },
#                         "snv_variant_caller_options": {
#                             "qc_detect_contamination": True,
#                             "vc_mnv_emit_component_calls": True,
#                             "vc_combine_phased_variants_distance": 2,
#                             "vc_combine_phased_variants_distance_snvs_only": 2
#                         },
#                         "sequence_data": {
#                             "fastq_list_rows": [
#                                 {
#                                     "rgid": "CTGCTTCC+GATCTATC.4.250328_A01052_0258_AHFGM7DSXF",
#                                     "rglb": "L2500373",
#                                     "rgsm": "L2500373",
#                                     "lane": 4,
#                                     "rgcn": "UMCCR",
#                                     "rgds": "Library ID: L2500373, Sequenced on 28 Mar, 2025 at UMCCR, Phenotype: normal, Assay: TsqNano, Type: WGS",
#                                     "rgdt": "2025-03-28T00:00:00",
#                                     "rgpl": "Illumina",
#                                     "read_1": {
#                                         "class": "File",
#                                         "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250328_A01052_0258_AHFGM7DSXF/20250402ebfe2c3d/Samples/Lane_4/L2500373/L2500373_S28_L004_R1_001.fastq.ora"
#                                     },
#                                     "read_2": {
#                                         "class": "File",
#                                         "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250328_A01052_0258_AHFGM7DSXF/20250402ebfe2c3d/Samples/Lane_4/L2500373/L2500373_S28_L004_R2_001.fastq.ora"
#                                     }
#                                 }
#                             ]
#                         },
#                         "sample_name": "L2500373",
#                         "reference": {
#                             "name": "hg38",
#                             "structure": "graph",
#                             "tarball": {
#                                 "class": "File",
#                                 "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz"
#                             }
#                         },
#                         "ora_reference": {
#                             "class": "File",
#                             "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz"
#                         }
#                     },
#                     "engineParameters": {
#                         "pipelineId": "d3228141-3753-40bc-8d22-ac91f1e37e75",
#                         "projectId": "eba5c946-1677-441d-bbce-6a11baadecbb",
#                         "outputUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/analysis/dragen-wgts-dna/20250617ac346b29/",
#                         "logsUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/logs/dragen-wgts-dna/20250617ac346b29/"
#                     },
#                     "tags": {
#                         "libraryId": "L2500373",
#                         "fastqRgidList": [
#                             "CTGCTTCC+GATCTATC.4.250328_A01052_0258_AHFGM7DSXF"
#                         ],
#                         "subjectId": "AIRSPACE-194-5",
#                         "individualId": "SBJ06472",
#                         "preLaunchCoverageEst": 34.79,
#                         "preLaunchDupFracEst": 0.26,
#                         "preLaunchInsertSizeEst": 286,
#                         "portalRunId": "20250617ac346b29"  # pragma: allowlist secret
#                     },
#                     "status": "SUCCEEDED",
#                     "submissionTime": "2025-06-18T00:36:06.918455",
#                     "stepsLaunchExecutionArn": "arn:aws:states:ap-southeast-2:472057503814:execution:icav2-wes-launchIcav2Analysis:8a76fee5-8d1a-43e6-9ad6-3deb368a87ba",
#                     "icav2AnalysisId": "72f51fcd-ab9c-4f61-80ca-e483f8dc58b6",
#                     "startTime": "2025-06-18T00:36:07.154707+00:00",
#                     "endTime": "2025-06-18T02:46:32.146135+00:00"
#                 }
#             },
#             None
#         ),
#         indent=4
#     ))
#
#     # {
#     #     "workflowRunStateChangeEvent": {
#     #         "status": "SUCCEEDED",
#     #         "timestamp": "2025-06-26T06:34:51Z",
#     #         "portalRunId": "20250617ac346b29",  // pragma: allowlist secret
#     #         "workflow": {
#     #             "orcabusId": "wfl.01JY07D115NZ0F4G1RKXMFEH46",
#     #             "workflowName": "dragen-wgts-dna",
#     #             "workflowVersion": "4.4.4",
#     #             "executionEngine": "Unknown",
#     #             "executionEnginePipelineId": "Unknown"
#     #         },
#     #         "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250617ac346b29",  // pragma: allowlist secret
#     #         "libraries": [
#     #             {
#     #                 "orcabusId": "lib.01JQ6MK7RZK96ZFH1C812FGCWJ",
#     #                 "libraryId": "L2500373"
#     #             }
#     #         ],
#     #         "payload": {
#     #             "version": "2025.06.06",
#     #             "data": {
#     #                 "tags": {
#     #                     "libraryId": "L2500373",
#     #                     "subjectId": "AIRSPACE-194-5",
#     #                     "individualId": "SBJ06472",
#     #                     "fastqRgidList": [
#     #                         "CTGCTTCC+GATCTATC.4.250328_A01052_0258_AHFGM7DSXF"
#     #                     ],
#     #                     "preLaunchDupFracEst": 0.26,
#     #                     "preLaunchCoverageEst": 34.79,
#     #                     "preLaunchInsertSizeEst": 286
#     #                 },
#     #                 "inputs": {
#     #                     "reference": {
#     #                         "name": "hg38",
#     #                         "tarball": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz",
#     #                         "structure": "graph"
#     #                     },
#     #                     "sampleName": "L2500373",
#     #                     "oraReference": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz",
#     #                     "sequenceData": {
#     #                         "fastqListRows": [
#     #                             {
#     #                                 "lane": 4,
#     #                                 "rgcn": "UMCCR",
#     #                                 "rgds": "Library ID: L2500373, Sequenced on 28 Mar, 2025 at UMCCR, Phenotype: normal, Assay: TsqNano, Type: WGS",
#     #                                 "rgdt": "2025-03-28T00:00:00",
#     #                                 "rgid": "CTGCTTCC+GATCTATC.4.250328_A01052_0258_AHFGM7DSXF",
#     #                                 "rglb": "L2500373",
#     #                                 "rgpl": "Illumina",
#     #                                 "rgsm": "L2500373",
#     #                                 "read1FileUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250328_A01052_0258_AHFGM7DSXF/20250402ebfe2c3d/Samples/Lane_4/L2500373/L2500373_S28_L004_R1_001.fastq.ora",
#     #                                 "read2FileUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250328_A01052_0258_AHFGM7DSXF/20250402ebfe2c3d/Samples/Lane_4/L2500373/L2500373_S28_L004_R2_001.fastq.ora"
#     #                             }
#     #                         ]
#     #                     },
#     #                     "alignmentOptions": {
#     #                         "enableDuplicateMarking": true
#     #                     },
#     #                     "targetedCallerOptions": {
#     #                         "enableTargeted": [
#     #                             "cyp2d6"
#     #                         ]
#     #                     },
#     #                     "snvVariantCallerOptions": {
#     #                         "qcDetectContamination": true,
#     #                         "vcMnvEmitComponentCalls": true,
#     #                         "vcCombinePhasedVariantsDistance": 2,
#     #                         "vcCombinePhasedVariantsDistanceSnvsOnly": 2
#     #                     }
#     #                 },
#     #                 "outputs": {
#     #                     "dragenGermlineAlignmentOutputRelPath": "L2500373__hg38__graph__dragen_alignment/",
#     #                     "dragenGermlineAlignmentOutputBamRelPath": "L2500373__hg38__graph__dragen_alignment/L2500373.bam",
#     #                     "dragenGermlineVariantCallingOutputRelPath": "L2500373__hg38__graph__dragen_variant_calling/",
#     #                     "dragenGermlineVariantCallingOutputSnvVcfRelPath": "L2500373__hg38__graph__dragen_variant_calling/L2500373.hard-filtered.vcf.gz",
#     #                     "multiQcOutputDir": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/analysis/dragen-wgts-dna/20250617ac346b29/L2500373_multiqc/",  // pragma: allowlist secret
#     #                     "multiQcHtmlReportUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/analysis/dragen-wgts-dna/20250617ac346b29/L2500373_multiqc/L2500373_multiqc_report.html"  // pragma: allowlist secret
#     #                 },
#     #                 "engineParameters": {
#     #                     "logsUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/logs/dragen-wgts-dna/20250617ac346b29/",  // pragma: allowlist secret
#     #                     "outputUri": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/analysis/dragen-wgts-dna/20250617ac346b29/",  // pragma: allowlist secret
#     #                     "projectId": "eba5c946-1677-441d-bbce-6a11baadecbb",
#     #                     "pipelineId": "d3228141-3753-40bc-8d22-ac91f1e37e75"
#     #                 }
#     #             }
#     #         }
#     #     }
#     # }
