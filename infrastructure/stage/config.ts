import {
  icav2ProjectId,
  pipelineCacheBucket,
  pipelineCachePrefix,
  StageName,
} from '@orcabus/platform-cdk-constructs/utils';
import {
  PAYLOAD_VERSION,
  SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
  SSM_PARAMETER_PATH_LOGS_PREFIX,
  SSM_PARAMETER_PATH_OUTPUT_PREFIX,
  SSM_PARAMETER_PATH_PAYLOAD_VERSION,
  SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
  SSM_PARAMETER_PATH_WORKFLOW_NAME,
  SSM_PARAMETER_PATH_WORKFLOW_VERSION,
  WORKFLOW_VERSION,
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
} from './constants';
import { StatefulApplicationStackConfig, StatelessApplicationStackConfig } from './interfaces';

/**
 * Stateful stack properties for the workflow.
 * Mainly just linking values from SSM parameters
 * @param stage
 */
export const getStatefulStackProps = (stage: StageName): StatefulApplicationStackConfig => {
  return {
    // Values
    workflowName: WORKFLOW_NAME,
    workflowVersion: WORKFLOW_VERSION,
    pipelineIdsByWorkflowVersionMap: WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP,
    icav2ProjectId: icav2ProjectId[stage],
    payloadVersion: PAYLOAD_VERSION,
    logsPrefix: WORKFLOW_LOGS_PREFIX.replace(
      /{__CACHE_BUCKET__}/g,
      pipelineCacheBucket[stage]
    ).replace(/{__CACHE_PREFIX__}/g, pipelineCachePrefix[stage]),
    outputPrefix: WORKFLOW_OUTPUT_PREFIX.replace(
      /{__CACHE_BUCKET__}/g,
      pipelineCacheBucket[stage]
    ).replace(/{__CACHE_PREFIX__}/g, pipelineCachePrefix[stage]),
    // Keys
    ssmParameterPaths: {
      ssmRootPrefix: SSM_PARAMETER_PATH_PREFIX,
      workflowName: SSM_PARAMETER_PATH_WORKFLOW_NAME,
      workflowVersion: SSM_PARAMETER_PATH_WORKFLOW_VERSION,
      prefixPipelineIdsByWorkflowVersion:
        SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
      icav2ProjectId: SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
      payloadVersion: SSM_PARAMETER_PATH_PAYLOAD_VERSION,
      logsPrefix: SSM_PARAMETER_PATH_LOGS_PREFIX,
      outputPrefix: SSM_PARAMETER_PATH_OUTPUT_PREFIX,
    },
  };
};

export const getStatelessStackProps = (): StatelessApplicationStackConfig => {
  return {
    // SSM Parameter Paths
    ssmParameterPaths: {
      ssmRootPrefix: SSM_PARAMETER_PATH_PREFIX,
      workflowName: SSM_PARAMETER_PATH_WORKFLOW_NAME,
      workflowVersion: SSM_PARAMETER_PATH_WORKFLOW_VERSION,
      prefixPipelineIdsByWorkflowVersion:
        SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION,
      icav2ProjectId: SSM_PARAMETER_PATH_ICAV2_PROJECT_ID,
      payloadVersion: SSM_PARAMETER_PATH_PAYLOAD_VERSION,
      logsPrefix: SSM_PARAMETER_PATH_LOGS_PREFIX,
      outputPrefix: SSM_PARAMETER_PATH_OUTPUT_PREFIX,
    },
    workflowName: WORKFLOW_NAME,
    eventBusName: EVENT_BUS_NAME,
    eventSource: EVENT_SOURCE,
    workflowRunStateChangeDetailType: WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE,
    icav2WesRequestDetailType: ICAV2_WES_REQUEST_DETAIL_TYPE,
    icav2WesStateChangeDetailType: ICAV2_WES_STATE_CHANGE_DETAIL_TYPE,
  };
};
