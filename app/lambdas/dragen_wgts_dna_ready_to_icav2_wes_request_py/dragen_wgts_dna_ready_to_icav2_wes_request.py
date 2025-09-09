#!/usr/bin/env python3

"""
BCLConvert InteropQC ready to ICAv2 WES request

Given a BCLConvert InteropQC ready event object, convert this to an ICAv2 WES request event detail

Inputs are as follows:

{
  // Workflow run status
  "status": "READY",
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
      },
      // Tags (same as bssh fastq to aws s3 copy succeeded event)
      "tags": {
       "instrumentRunId": "20231010_pi1-07_0329_A222N7LTD3"
      }
    }
  }
}

With the outputs as follows:

{
  // The workflow run name
  "name": "umccr--automated--bclconvert-interop-qc--2024-05-24--20250417abcd1234",
  "inputs": {
    // Because this runs as a CWL workflow, we need to provide the inputs in a specific format
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
  // The engine parameters are used to launch the BCLConvert InterOp QC Manager workflow on ICAv2
  "engineParameters": {
    // The output URI is used to identify the BCLConvert InterOp QC Manager workflow
    "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/analysis/bclconvert-interop-qc/20250417abcd1234/",
    // This is where the ICA Logs will be stored
    "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/logs/bclconvert-interop-qc/20250417abcd1234/",
    // The ICAv2 Project ID we use to launch the workflow
    // Provided in the READY event
    // If not we can collect this from the platform cdk constructs
    "projectId": "uuid4",
    // Pipeline Id
    // Provided in the READY event
    // If not we can collect this from the platform cdk constructs
    "pipelineId": "uuid4"
  },
  // Tags (same as bssh fastq to aws s3 copy succeeded event)
  "tags": {
   "instrumentRunId": "20231010_pi1-07_0329_A222N7LTD3"
  }
}

We also get the optional default inputs from SSM, the pipeline id and the project id

"""

from typing import Dict, Any


def to_snake_case(s: str) -> str:
    """
    Convert a string to snake_case.
    :param s: The input string.
    :return: The snake_case version of the input string.
    """
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')


def recursive_snake_case(d: Dict[str, Any]) -> Any:
    """
    Convert all keys in a dictionary to snake_case recursively.
    If the value is a list, we also need to convert each item in the list if it is a dictionary.
    :param d:
    :return:
    """
    if not isinstance(d, dict) and not isinstance(d, list):
        return d

    if isinstance(d, dict):
        return {to_snake_case(k): recursive_snake_case(v) for k, v in d.items()}

    return [recursive_snake_case(item) for item in d]


def update_fqlr_input_name(input_name: str) -> str:
    if input_name == 'read1FileUri':
        return 'read_1'
    if input_name == 'read2FileUri':
        return 'read_2'
    return input_name


def cwlify_file(file_uri: str) -> Dict[str, str]:
    return {
        "class": "File",
        "location": file_uri
    }


def handler(event, context) -> Dict[str, Any]:
    """
    Convert the BCLConvert InteropQC ready event to an ICAv2 WES request event detail.
    :param event:
    :param context:
    :return:
    """
    event_detail_body = event['dragenWgtsDnaReadyEventDetail']

    # Get inputs
    inputs = event_detail_body['payload']['data']['inputs']

    # If sequenceData contains either fastqListRows or tumorFastqListRows, we need to edit to CWL file types
    for sequence_data_key_iter_ in ['sequenceData', 'tumorSequenceData']:
        if 'fastqListRows' not in inputs.get(sequence_data_key_iter_, {}):
            continue
        inputs[sequence_data_key_iter_]['fastqListRows'] = list(map(
            lambda fqlr_iter_: dict(map(
                lambda fqlr_item: (
                    (update_fqlr_input_name(fqlr_item[0]), cwlify_file(fqlr_item[1]))
                    if not update_fqlr_input_name(fqlr_item[0]) == fqlr_item[0]
                    else
                    (fqlr_item[0], fqlr_item[1])  # Keep the original key if it is not read1FileUri or read2FileUri
                ),
                fqlr_iter_.items()
            )),
            inputs[sequence_data_key_iter_]['fastqListRows']
        ))

    # Update references
    inputs['reference']['tarball'] = cwlify_file(inputs['reference']['tarball'])
    if 'oraReference' in inputs:
        inputs['oraReference'] = cwlify_file(inputs['oraReference'])
    if 'somaticReference' in inputs:
        inputs['somaticReference']['tarball'] = cwlify_file(inputs['somaticReference']['tarball'])

    if (
            'somaticMsiOptions' in inputs and
            'msiMicrosatellitesFile' in inputs['somaticMsiOptions']
    ):
        inputs['somaticMsiOptions']['msiMicrosatellitesFile'] = cwlify_file(inputs['somaticMsiOptions']['msiMicrosatellitesFile'])

    # Update variant annotation data to a file object
    if (
            'nirvanaAnnotationOptions' in inputs and
            'variantAnnotationData' in inputs['nirvanaAnnotationOptions']
    ):
        inputs['nirvanaAnnotationOptions']['variantAnnotationData'] = cwlify_file(
            inputs['nirvanaAnnotationOptions']['variantAnnotationData']
        )

    # Update somatic variant annotation data to a file object
    if (
            'somaticNirvanaAnnotationOptions' in inputs and
            'variantAnnotationData' in inputs['somaticNirvanaAnnotationOptions']
    ):
        inputs['somaticNirvanaAnnotationOptions']['variantAnnotationData'] = cwlify_file(
            inputs['somaticNirvanaAnnotationOptions']['variantAnnotationData']
        )

    # Convert all keys to snake_case recursively
    inputs = recursive_snake_case(inputs)

    # Extract the inputs from the event detail body
    return {
        "icav2WesRequestEventDetail": {
            "name": event_detail_body['workflowRunName'],
            "inputs": inputs,
            "engineParameters": event_detail_body['payload']['data']['engineParameters'],
            "tags": {
                # Copy all other tags from the event detail body
                **event_detail_body['payload']['data']['tags'],
                # Add the portal run ID to the tags
                "portalRunId": event_detail_body['portalRunId']
            }
        }
    }


# if __name__ == "__main__":
#     import json
#
#     print(
#         json.dumps(
#             handler(
#                 event={
#                     "dragenWgtsDnaReadyEventDetail": {
#                         "portalRunId": "20250606efgh1234",
#                         "timestamp": "2025-06-06T04:39:31+00:00",
#                         "status": "READY",
#                         "workflowName": "dragen-wgts-dna",
#                         "workflowVersion": "4.4.4",
#                         "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606efgh1234",
#                         "linkedLibraries": [
#                             {
#                                 "libraryId": "L2301197",
#                                 "orcabusId": "lib.01JBMVHM2D5GCC7FTC20K4FDFK"
#                             }
#                         ],
#                         "payload": {
#                             "refId": "4d8b4468-55da-490f-8aab-0adcaed3fc33",
#                             "version": "2025.06.06",
#                             "data": {
#                                 "inputs": {
#                                     "alignmentOptions": {
#                                         "enableDuplicateMarking": True
#                                     },
#                                     "reference": {
#                                         "name": "hg38",
#                                         "structure": "graph",
#                                         "tarball": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz"
#                                     },
#                                     "oraReference": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz",
#                                     "sampleName": "L2301197",
#                                     "targetedCallerOptions": {
#                                         "enableTargeted": [
#                                             "cyp2d6"
#                                         ]
#                                     },
#                                     "sequenceData": {
#                                         "fastqListRows": [
#                                             {
#                                                 "rgid": "L2301197",
#                                                 "rglb": "L2301197",
#                                                 "rgsm": "L2301197",
#                                                 "lane": 1,
#                                                 "read1FileUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R1_001.fastq.ora",
#                                                 "read2FileUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R2_001.fastq.ora"
#                                             }
#                                         ]
#                                     },
#                                     "snv_variant_caller_options": {
#                                         "enableVcfCompression": True,
#                                         "enableVcfIndexing": True,
#                                         "qcDetectContamination": True,
#                                         "vcMnvEmitComponentCalls": True,
#                                         "vcCombinePhasedVariantsDistance": 2,
#                                         "vcCombinePhasedVariantsDistanceSnvsOnly": 2
#                                     }
#                                 },
#                                 "engineParameters": {
#                                     "pipelineId": "5009335a-8425-48a8-83c4-17c54607b44a",
#                                     "projectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4",
#                                     "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/analysis/dragen-wgts-dna/20250606efgh1234/",
#                                     "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/logs/dragen-wgts-dna/20250606efgh1234/"
#                                 },
#                                 "tags": {
#                                     "libraryId": "L2301197"
#                                 }
#                             }
#                         }
#                     },
#                     "defaultPipelineId": "5009335a-8425-48a8-83c4-17c54607b44a",
#                     "defaultProjectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4"
#                 },
#                 context=None
#             ),
#             indent=4
#         )
#     )
#
#     # {
#     #     "icav2WesRequestEventDetail": {
#     #         "name": "umccr--automated--dragen-wgts-dna--4-4-4--20250606efgh1234",
#     #         "inputs": {
#     #             "alignment_options": {
#     #                 "enable_duplicate_marking": true
#     #             },
#     #             "reference": {
#     #                 "name": "hg38",
#     #                 "structure": "graph",
#     #                 "tarball": {
#     #                     "class": "File",
#     #                     "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz"
#     #                 }
#     #             },
#     #             "ora_reference": {
#     #                 "class": "File",
#     #                 "location": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz"
#     #             },
#     #             "sample_name": "L2301197",
#     #             "targeted_caller_options": {
#     #                 "enable_targeted": [
#     #                     "cyp2d6"
#     #                 ]
#     #             },
#     #             "sequence_data": {
#     #                 "fastq_list_rows": [
#     #                     {
#     #                         "rgid": "L2301197",
#     #                         "rglb": "L2301197",
#     #                         "rgsm": "L2301197",
#     #                         "lane": 1,
#     #                         "read_1": {
#     #                             "class": "File",
#     #                             "location": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R1_001.fastq.ora"
#     #                         },
#     #                         "read_2": {
#     #                             "class": "File",
#     #                             "location": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R2_001.fastq.ora"
#     #                         }
#     #                     }
#     #                 ]
#     #             },
#     #             "snv_variant_caller_options": {
#     #                 "enable_vcf_compression": true,
#     #                 "enable_vcf_indexing": true,
#     #                 "qc_detect_contamination": true,
#     #                 "vc_mnv_emit_component_calls": true,
#     #                 "vc_combine_phased_variants_distance": 2,
#     #                 "vc_combine_phased_variants_distance_snvs_only": 2
#     #             }
#     #         },
#     #         "engineParameters": {
#     #             "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/analysis/dragen-wgts-dna/20250606efgh1234/",
#     #             "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/logs/dragen-wgts-dna/20250606efgh1234/",
#     #             "projectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4",
#     #             "pipelineId": "5009335a-8425-48a8-83c4-17c54607b44a"
#     #         },
#     #         "tags": {
#     #             "libraryId": "L2301197",
#     #             "portalRunId": "20250606efgh1234"
#     #         }
#     #     }
#     # }
