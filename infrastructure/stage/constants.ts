/* Directory constants */
import path from 'path';
import { OraReferenceVersionType, Reference, WorkflowVersionType } from './interfaces';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';

export const APP_ROOT = path.join(__dirname, '../../app');
export const LAMBDA_DIR = path.join(APP_ROOT, 'lambdas');
export const STEP_FUNCTIONS_DIR = path.join(APP_ROOT, 'step-functions-templates');
export const EVENT_SCHEMAS_DIR = path.join(APP_ROOT, 'event-schemas');

/* Stack constants */
export const STACK_PREFIX = 'orca-dragen-wgts-dna';

/* Workflow constants */
export const WORKFLOW_NAME = 'dragen-wgts-dna';
export const DEFAULT_WORKFLOW_VERSION: WorkflowVersionType = '4.4.4';
export const DEFAULT_PAYLOAD_VERSION = '2025.06.04';
export const DEFAULT_ORA_VERSION = '2.7.0';

export const WORKFLOW_LOGS_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}logs/${WORKFLOW_NAME}/`;
export const WORKFLOW_OUTPUT_PREFIX = `s3://{__CACHE_BUCKET__}/{__CACHE_PREFIX__}analysis/${WORKFLOW_NAME}/`;

/* We extend this every time we release a new version of the workflow */
/* This is added into our SSM Parameter Store to allow us to map workflow versions to pipeline IDs */
export const WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP: Record<
  WorkflowVersionType,
  string
> = {
  // https://github.com/umccr/cwl-ica/releases/tag/dragen-wgts-dna-pipeline%2F4.4.4__20250831041955
  '4.4.4': 'c8a273d6-bd83-44de-b2b7-3df53d21b278',
};

export const WORKFLOW_VERSION_TO_DEFAULT_REFERENCE_PATHS_MAP: Record<
  WorkflowVersionType,
  Reference
> = {
  '4.4.4': {
    name: 'hg38',
    structure: 'graph',
    tarball:
      's3://reference-data-503977275616-ap-southeast-2/refdata/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz',
  },
};

export const WORKFLOW_VERSION_TO_DEFAULT_SOMATIC_REFERENCE_PATHS_MAP: Record<
  WorkflowVersionType,
  Reference
> = {
  '4.4.4': {
    name: 'hg38',
    structure: 'linear',
    tarball:
      's3://reference-data-503977275616-ap-southeast-2/refdata/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-hla-methyl_cg-methylated_combined/hg38-alt_masked.cnv.hla.methyl_cg.methylated_combined.rna-11-r5.0-1.tar.gz',
  },
};

export const ORA_VERSION_TO_DEFAULT_ORA_REFERENCE_PATHS_MAP: Record<
  OraReferenceVersionType,
  string
> = {
  '2.7.0':
    's3://reference-data-503977275616-ap-southeast-2/refdata/dragen-ora/v2/ora_reference_v2.tar.gz',
};

export const MSI_REFERENCE_PATH_MAP: Record<WorkflowVersionType, string> = {
  '4.4.4':
    's3://reference-data-503977275616-ap-southeast-2/refdata/dragen-msi/1-1-0/hg38/WGS_v1.1.0_hg38_microsatellites.list',
};

export const DEFAULT_WORKFLOW_INPUTS_BY_VERSION_MAP: Record<WorkflowVersionType, object> = {
  '4.4.4': {
    alignmentOptions: {
      enableDuplicateMarking: true,
    },
    targetedCallerOptions: {
      enableTargeted: ['cyp2d6'],
    },
    snvVariantCallerOptions: {
      qcDetectContamination: true,
      vcMnvEmitComponentCalls: true,
      vcCombinePhasedVariantsDistance: 2,
      vcCombinePhasedVariantsDistanceSnvsOnly: 2,
    },
    somaticCnvCallerOptions: {
      enableCnv: true,
      enableHrd: true,
      cnvUseSomaticVcBaf: true,
    },
    somaticSvCallerOptions: {
      enableSv: true,
    },
    somaticMsiOptions: {
      msiCommand: 'tumor-normal',
      msiMicrosatellitesFile: MSI_REFERENCE_PATH_MAP['4.4.4'],
      // 40 suggested here - https://help.dragen.illumina.com/product-guide/dragen-v4.4/dragen-recipes/dna-somatic-tumor-normal-solid-wgs#msi
      msiCoverageThreshold: 40, // Default is 60 (allegedly) but it's not actually a default
    },
    // TMB Requires nirvana annotation data
    somaticNirvanaAnnotationOptions: {
      enableVariantAnnotation: true,
      variantAnnotationAssembly: 'GRCh38',
    },
    somaticTmbOptions: {
      enableTmb: true,
    },
  },
};

/* SSM Parameter Paths */
export const SSM_PARAMETER_PATH_PREFIX = path.join('/orcabus/workflows/dragen-wgts-dna/');
// Workflow Parameters
export const SSM_PARAMETER_PATH_WORKFLOW_NAME = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'workflow-name'
);
export const SSM_PARAMETER_PATH_DEFAULT_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'default-workflow-version'
);
// Input parameters
export const SSM_PARAMETER_PATH_PREFIX_INPUTS_BY_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'inputs-by-workflow-version'
);
// Engine Parameters
export const SSM_PARAMETER_PATH_PREFIX_PIPELINE_IDS_BY_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'pipeline-ids-by-workflow-version'
);
export const SSM_PARAMETER_PATH_ICAV2_PROJECT_ID = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'icav2-project-id'
);
export const SSM_PARAMETER_PATH_PAYLOAD_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'payload-version'
);
export const SSM_PARAMETER_PATH_LOGS_PREFIX = path.join(SSM_PARAMETER_PATH_PREFIX, 'logs-prefix');
export const SSM_PARAMETER_PATH_OUTPUT_PREFIX = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'output-prefix'
);
// Reference Parameters
export const SSM_PARAMETER_PATH_PREFIX_REFERENCE_PATHS_BY_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'default-reference-paths-by-workflow-version'
);
export const SSM_PARAMETER_PATH_PREFIX_SOMATIC_REFERENCE_PATHS_BY_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'default-somatic-reference-paths-by-workflow-version'
);
export const SSM_PARAMETER_PATH_PREFIX_ORA_REFERENCE_PATHS_BY_WORKFLOW_VERSION = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'ora-reference-paths-by-ora-version'
);

/* Event Constants */
export const EVENT_BUS_NAME = 'OrcaBusMain';
export const EVENT_SOURCE = 'orcabus.dragenwgtsdna';
export const WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE = 'WorkflowRunStateChange';
export const WORKFLOW_RUN_UPDATE_DETAIL_TYPE = 'WorkflowRunUpdate';
export const ICAV2_WES_REQUEST_DETAIL_TYPE = 'Icav2WesRequest';
export const ICAV2_WES_STATE_CHANGE_DETAIL_TYPE = 'Icav2WesAnalysisStateChange';

export const WORKFLOW_MANAGER_EVENT_SOURCE = 'orcabus.workflowmanager';
export const ICAV2_WES_EVENT_SOURCE = 'orcabus.icav2wesmanager';
export const FASTQ_SYNC_DETAIL_TYPE = 'FastqSync';

/* Event rule constants */
export const DRAFT_STATUS = 'DRAFT';
export const READY_STATUS = 'READY';

/* Schema constants */
export const SCHEMA_REGISTRY_NAME = EVENT_SOURCE;
export const SSM_SCHEMA_ROOT = path.join(SSM_PARAMETER_PATH_PREFIX, 'schemas');

/* Future proofing */
export const NEW_WORKFLOW_MANAGER_IS_DEPLOYED: Record<StageName, boolean> = {
  BETA: true,
  GAMMA: false,
  PROD: false,
};
