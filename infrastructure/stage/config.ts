import {
  DEFAULT_PAYLOAD_VERSION,
  SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
  SSM_PARAMETER_PATH_LOGS_PREFIX,
  SSM_PARAMETER_PATH_OUTPUT_PREFIX,
  SSM_PARAMETER_PATH_PAYLOAD_VERSION,
  SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
  SSM_PARAMETER_PATH_WORKFLOW_NAME,
  SSM_PARAMETER_PATH_DEFAULT_WORKFLOW_VERSION,
  DEFAULT_WORKFLOW_VERSION,
  WORKFLOW_LOGS_PREFIX,
  WORKFLOW_NAME,
  WORKFLOW_OUTPUT_PREFIX,
  WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP,
  EVENT_BUS_NAME,
  EVENT_SOURCE,
  WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE,
  ICAV2_WES_REQUEST_DETAIL_TYPE,
  ICAV2_WES_STATE_CHANGE_DETAIL_TYPE,
  SSM_PARAMETER_PATH_PREFIX,
  SSM_PARAMETER_PATH_PREFIX_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
  SSM_PARAMETER_PATH_PREFIX_SOMATIC_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
  SSM_PARAMETER_PATH_PREFIX_ORA_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
  WORKFLOW_VERSION_TO_DEFAULT_REFERENCE_PATHS_MAP,
  WORKFLOW_VERSION_TO_DEFAULT_SOMATIC_REFERENCE_PATHS_MAP,
  ORA_VERSION_TO_DEFAULT_ORA_REFERENCE_PATHS_MAP,
  SSM_PARAMETER_PATH_PREFIX_INPUTS_BY_WORKFLOW_VERSION,
  DEFAULT_WORKFLOW_INPUTS_BY_VERSION_MAP,
} from './constants';
import { StatefulApplicationStackConfig, StatelessApplicationStackConfig } from './interfaces';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';
import { ICAV2_PROJECT_ID } from '@orcabus/platform-cdk-constructs/shared-config/icav2';
import {
  PIPELINE_CACHE_BUCKET,
  PIPELINE_CACHE_PREFIX,
} from '@orcabus/platform-cdk-constructs/shared-config/s3';

/**
 * Stateful stack properties for the workflow.
 * Mainly just linking values from SSM parameters
 * @param stage
 */
export const getStatefulStackProps = (stage: StageName): StatefulApplicationStackConfig => {
  return {
    ssmParameterValues: {
      // Values
      // Detail
      workflowName: WORKFLOW_NAME,
      workflowVersion: DEFAULT_WORKFLOW_VERSION,

      // Payload
      payloadVersion: DEFAULT_PAYLOAD_VERSION,

      // Inputs
      inputsByWorkflowVersionMap: DEFAULT_WORKFLOW_INPUTS_BY_VERSION_MAP,

      // Engine Parameters
      pipelineIdsByWorkflowVersionMap: WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP,
      icav2ProjectId: ICAV2_PROJECT_ID[stage],
      logsPrefix: WORKFLOW_LOGS_PREFIX.replace(
        /{__CACHE_BUCKET__}/g,
        PIPELINE_CACHE_BUCKET[stage]
      ).replace(/{__CACHE_PREFIX__}/g, PIPELINE_CACHE_PREFIX[stage]),
      outputPrefix: WORKFLOW_OUTPUT_PREFIX.replace(
        /{__CACHE_BUCKET__}/g,
        PIPELINE_CACHE_BUCKET[stage]
      ).replace(/{__CACHE_PREFIX__}/g, PIPELINE_CACHE_PREFIX[stage]),

      // References
      referenceByWorkflowVersionMap: WORKFLOW_VERSION_TO_DEFAULT_REFERENCE_PATHS_MAP,
      somaticReferenceByWorkflowVersionMap: WORKFLOW_VERSION_TO_DEFAULT_SOMATIC_REFERENCE_PATHS_MAP,
      oraCompressionByWorkflowVersionMap: ORA_VERSION_TO_DEFAULT_ORA_REFERENCE_PATHS_MAP,
    },
    // Keys
    ssmParameterPaths: {
      // Top level prefix
      ssmRootPrefix: SSM_PARAMETER_PATH_PREFIX,

      // Detail
      workflowName: SSM_PARAMETER_PATH_WORKFLOW_NAME,
      workflowVersion: SSM_PARAMETER_PATH_DEFAULT_WORKFLOW_VERSION,

      // Inputs
      prefixDefaultInputsByWorkflowVersion: SSM_PARAMETER_PATH_PREFIX_INPUTS_BY_WORKFLOW_VERSION,

      // Payload
      payloadVersion: SSM_PARAMETER_PATH_PAYLOAD_VERSION,

      // Engine Parameters
      prefixPipelineIdsByWorkflowVersion:
        SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
      icav2ProjectId: SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
      logsPrefix: SSM_PARAMETER_PATH_LOGS_PREFIX,
      outputPrefix: SSM_PARAMETER_PATH_OUTPUT_PREFIX,

      // Reference SSM Paths
      referenceSsmRootPrefix: SSM_PARAMETER_PATH_PREFIX_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
      somaticReferenceSsmRootPrefix:
        SSM_PARAMETER_PATH_PREFIX_SOMATIC_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
      oraCompressionSsmRootPrefix:
        SSM_PARAMETER_PATH_PREFIX_ORA_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
    },
  };
};

export const getStatelessStackProps = (): StatelessApplicationStackConfig => {
  return {
    // SSM Parameter Paths
    ssmParameterPaths: {
      // Top level prefix
      ssmRootPrefix: SSM_PARAMETER_PATH_PREFIX,

      // Detail
      workflowName: SSM_PARAMETER_PATH_WORKFLOW_NAME,
      workflowVersion: SSM_PARAMETER_PATH_DEFAULT_WORKFLOW_VERSION,

      // Inputs
      prefixDefaultInputsByWorkflowVersion: SSM_PARAMETER_PATH_PREFIX_INPUTS_BY_WORKFLOW_VERSION,

      // Payload
      payloadVersion: SSM_PARAMETER_PATH_PAYLOAD_VERSION,

      // Engine Parameters
      prefixPipelineIdsByWorkflowVersion:
        SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
      icav2ProjectId: SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
      logsPrefix: SSM_PARAMETER_PATH_LOGS_PREFIX,
      outputPrefix: SSM_PARAMETER_PATH_OUTPUT_PREFIX,

      // Reference SSM Paths
      referenceSsmRootPrefix: SSM_PARAMETER_PATH_PREFIX_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
      somaticReferenceSsmRootPrefix:
        SSM_PARAMETER_PATH_PREFIX_SOMATIC_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
      oraCompressionSsmRootPrefix:
        SSM_PARAMETER_PATH_PREFIX_ORA_REFERENCE_PATHS_BY_WORKFLOW_VERSION,
    },

    // Event
    eventSource: EVENT_SOURCE,
    workflowRunStateChangeDetailType: WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE,

    // SSM Parameter Values
    // Detail
    workflowName: WORKFLOW_NAME,
    eventBusName: EVENT_BUS_NAME,

    icav2WesRequestDetailType: ICAV2_WES_REQUEST_DETAIL_TYPE,
    icav2WesStateChangeDetailType: ICAV2_WES_STATE_CHANGE_DETAIL_TYPE,
  };
};
