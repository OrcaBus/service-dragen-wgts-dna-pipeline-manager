/* Directory constants */
import path from 'path';
import { Reference } from './interfaces';

export const APP_ROOT = path.join(__dirname, '../../app');
export const LAMBDA_DIR = path.join(APP_ROOT, 'lambdas');
export const STEP_FUNCTIONS_DIR = path.join(APP_ROOT, 'step-functions-templates');

/* Workflow constants */
export const WORKFLOW_NAME = 'dragen-wgts-dna';
export const DEFAULT_WORKFLOW_VERSION = '4.4.4';
export const DEFAULT_PAYLOAD_VERSION = '2025.06.04';
export const DEFAULT_ORA_VERSION = '2.7.0';

export const WORKFLOW_LOGS_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}logs/${WORKFLOW_NAME}/`;
export const WORKFLOW_OUTPUT_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}analysis/${WORKFLOW_NAME}/`;

/* We extend this every time we release a new version of the workflow */
/* This is added into our SSM Parameter Store to allow us to map workflow versions to pipeline IDs */
export const WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP: Record<string, string> = {
  // FIXME!! - Pipeline ID is right, but we don't have a tagged release for this version yet.
  // https://github.com/umccr/cwl-ica/releases/tag/bclconvert-interop-qc%2F1.3.1--1.25.2__20250414112602
  '4.4.4': '5009335a-8425-48a8-83c4-17c54607b44a',
};

export const WORKFLOW_VERSION_TO_DEFAULT_REFERENCE_PATHS_MAP: Record<string, Reference> = {
  '4.4.4': {
    name: 'hg38',
    structure: 'graph',
    tarball:
      's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz',
  },
};

export const WORKFLOW_VERSION_TO_DEFAULT_SOMATIC_REFERENCE_PATHS_MAP: Record<string, Reference> = {
  '4.4.4': {
    name: 'hg38',
    structure: 'linear',
    tarball:
      's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz',
  },
};

export const ORA_VERSION_TO_DEFAULT_ORA_REFERENCE_PATHS_MAP: Record<string, string> = {
  '2.7.0':
    's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz',
};

/* SSM Parameter Paths */
export const SSM_PARAMETER_PATH_PREFIX = '/orcabus/workflows/dragen-wgts-dna/';
// Workflow Parameters
export const SSM_PARAMETER_PATH_WORKFLOW_NAME = `${SSM_PARAMETER_PATH_PREFIX}workflow-name`;
export const SSM_PARAMETER_PATH_DEFAULT_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}default-workflow-version`;
// Engine Parameters
export const SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}pipeline-ids-by-workflow-version/`;
export const SSM_PARAMETER_PATH_ICAV2_PROJECT_ID = `${SSM_PARAMETER_PATH_PREFIX}icav2-project-id`;
export const SSM_PARAMETER_PATH_PAYLOAD_VERSION = `${SSM_PARAMETER_PATH_PREFIX}payload-version`;
export const SSM_PARAMETER_PATH_LOGS_PREFIX = `${SSM_PARAMETER_PATH_PREFIX}logs-prefix`;
export const SSM_PARAMETER_PATH_OUTPUT_PREFIX = `${SSM_PARAMETER_PATH_PREFIX}output-prefix`;
// Reference Parameters
export const SSM_PARAMETER_PATH_PREFIX_REFERENCE_PATHS_BY_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}default-reference-paths-by-workflow-version/`;
export const SSM_PARAMETER_PATH_PREFIX_SOMATIC_REFERENCE_PATHS_BY_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}default-somatic-reference-paths-by-workflow-version/`;
export const SSM_PARAMETER_PATH_PREFIX_ORA_REFERENCE_PATHS_BY_WORKFLOW_VERSION = `${SSM_PARAMETER_PATH_PREFIX}ora-reference-paths-by-ora-version/`;

/* Event Constants */
export const EVENT_BUS_NAME = 'OrcaBusMain';
export const EVENT_SOURCE = 'orcabus.dragenwgtsdna';
export const WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE = 'WorkflowRunStateChange';
export const ICAV2_WES_REQUEST_DETAIL_TYPE = 'Icav2WesRequest';
export const ICAV2_WES_STATE_CHANGE_DETAIL_TYPE = 'Icav2WesAnalysisStateChange';

export const WORKFLOW_MANAGER_EVENT_SOURCE = 'orcabus.workflowmanager';
export const ICAV2_WES_EVENT_SOURCE = 'orcabus.icav2wesmanager';
export const FASTQ_SYNC_DETAIL_TYPE = 'fastqSync';

/* Event rule constants */
export const DRAFT_STATUS = 'DRAFT';
export const READY_STATUS = 'READY';
