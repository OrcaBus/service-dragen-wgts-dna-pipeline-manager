/* Directory constants */
import path from 'path';
export const APP_ROOT = path.join(__dirname, '../../app');
export const LAMBDA_DIR = path.join(APP_ROOT, 'lambdas');
export const STEP_FUNCTIONS_DIR = path.join(APP_ROOT, 'step-functions-templates');

/* Workflow constants */
export const WORKFLOW_NAME = 'dragen-wgts-dna';
export const WORKFLOW_VERSION = '4.4.4';
export const PAYLOAD_VERSION = '2025.06.04';

export const WORKFLOW_LOGS_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}/logs/${WORKFLOW_NAME}/`;
export const WORKFLOW_OUTPUT_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}/analysis/${WORKFLOW_NAME}/`;

/* We extend this every time we release a new version of the workflow */
/* This is added into our SSM Parameter Store to allow us to map workflow versions to pipeline IDs */
export const WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP: Record<string, string> = {
  // FIXME!!
  // https://github.com/umccr/cwl-ica/releases/tag/bclconvert-interop-qc%2F1.3.1--1.25.2__20250414112602
  '4.4.4': '355dc03f-31a3-4162-a96f-f8f954b1f63e',
};

/* SSM Parameter Paths */
export const SSM_PARAMETER_PATH_PREFIX = '/orcabus/workflows/dragen-wgts-dna/';
export const SSM_PARAMETER_PATH_WORKFLOW_NAME = `${SSM_PARAMETER_PATH_PREFIX}${WORKFLOW_NAME}`;
export const SSM_PARAMETER_PATH_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}${WORKFLOW_VERSION}`;
export const SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}pipeline-ids-by-workflow-version/`;
export const SSM_PARAMETER_PATH_ICAV2_PROJECT_ID = `${SSM_PARAMETER_PATH_PREFIX}icav2-project-id`;
export const SSM_PARAMETER_PATH_PAYLOAD_VERSION = `${SSM_PARAMETER_PATH_PREFIX}payload-version`;
export const SSM_PARAMETER_PATH_LOGS_PREFIX = `${SSM_PARAMETER_PATH_PREFIX}logs-prefix`;
export const SSM_PARAMETER_PATH_OUTPUT_PREFIX = `${SSM_PARAMETER_PATH_PREFIX}output-prefix`;

/* Event Constants */
export const EVENT_BUS_NAME = 'OrcaBusMain';
export const EVENT_SOURCE = 'orcabus.dragenwgtsdna';
export const WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE = 'WorkflowRunStateChange';
export const ICAV2_WES_REQUEST_DETAIL_TYPE = 'Icav2WesRequest';
export const ICAV2_WES_STATE_CHANGE_DETAIL_TYPE = 'Icav2WesAnalysisStateChange';

export const WORKFLOW_MANAGER_EVENT_SOURCE = 'orcabus.workflowmanager';
export const ICAV2_WES_EVENT_SOURCE = 'orcabus.icav2wesmanager';

/* Event rule constants */
export const READY_STATUS = 'READY';
