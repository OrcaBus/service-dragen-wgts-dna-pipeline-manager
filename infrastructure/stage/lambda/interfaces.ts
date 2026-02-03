import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';

/**
 * Lambda function interface.
 */
export type LambdaNameList =
  // Pre-Draft Lambda functions
  | 'generateWorkflowRunNameAndPortalRunId'
  // Pre-Draft-complete Lambda functions
  | 'getLibraries'
  | 'getMetadataTags'
  | 'getProjectBaseUriFromProjectId'
  | 'getFastqListRowsFromRgidList'
  | 'getFastqRgidsFromLibraryId'
  | 'getFastqIdListFromRgidList'
  | 'getQcSummaryStatsFromRgidList'
  | 'checkNtsmInternal'
  | 'checkNtsmExternal'
  // Validation Functions
  | 'validateDraftCompleteSchema'
  | 'postSchemaValidation'
  // Pre-READY Lambda functions
  // Pre-submission Lambda functions
  | 'dragenWgtsDnaReadyToIcav2WesRequest'
  // Post-submission Lambda functions/
  | 'convertIcav2WesStateChangeEventToWrscEvent'
  | 'addPostAnalysisTags'
  | 'addWesFailureComment';

export const lambdaNameList: LambdaNameList[] = [
  // Pre-Draft Lambda functions
  'generateWorkflowRunNameAndPortalRunId',
  // Pre-ready Lambda functions
  'getLibraries',
  'getMetadataTags',
  'getProjectBaseUriFromProjectId',
  'getFastqListRowsFromRgidList',
  'getFastqRgidsFromLibraryId',
  'getFastqIdListFromRgidList',
  'getQcSummaryStatsFromRgidList',
  'checkNtsmInternal',
  'checkNtsmExternal',
  // Validation Functions
  'validateDraftCompleteSchema',
  'postSchemaValidation',
  // Pre-submission Lambda functions
  'dragenWgtsDnaReadyToIcav2WesRequest',
  // Post-submission Lambda functions/
  'convertIcav2WesStateChangeEventToWrscEvent',
  'addPostAnalysisTags',
  'addWesFailureComment',
];

// Requirements interface for Lambda functions
export interface LambdaRequirements {
  needsOrcabusApiTools?: boolean;
  needsIcav2Tools?: boolean;
  needsSsmParametersAccess?: boolean;
  needsSchemaRegistryAccess?: boolean;
  needsExternalBucketInfo?: boolean;
}

// Lambda requirements mapping
export const lambdaRequirementsMap: Record<LambdaNameList, LambdaRequirements> = {
  // Needs Orcabus API tools to generate the workflow run name and portal run ID
  generateWorkflowRunNameAndPortalRunId: { needsOrcabusApiTools: true },
  // Pre-draft-complete Lambda functions
  getMetadataTags: {
    needsOrcabusApiTools: true,
  },
  getLibraries: {
    needsOrcabusApiTools: true,
  },
  getFastqListRowsFromRgidList: {
    needsOrcabusApiTools: true,
    needsExternalBucketInfo: true,
  },
  getFastqRgidsFromLibraryId: {
    needsOrcabusApiTools: true,
  },
  getFastqIdListFromRgidList: {
    needsOrcabusApiTools: true,
  },
  getProjectBaseUriFromProjectId: {
    needsIcav2Tools: true,
  },
  getQcSummaryStatsFromRgidList: {
    needsOrcabusApiTools: true,
  },
  checkNtsmInternal: {
    needsOrcabusApiTools: true,
  },
  checkNtsmExternal: {
    needsOrcabusApiTools: true,
  },
  // Validation Functions
  validateDraftCompleteSchema: {
    needsSchemaRegistryAccess: true,
    needsSsmParametersAccess: true,
    needsOrcabusApiTools: true,
  },
  postSchemaValidation: {
    needsOrcabusApiTools: true,
    needsIcav2Tools: true,
    needsExternalBucketInfo: true,
  },
  // Pre-submission Lambda functions
  dragenWgtsDnaReadyToIcav2WesRequest: {},
  // Needs Orcabus API tools to fetch the existing workflow run state
  convertIcav2WesStateChangeEventToWrscEvent: { needsOrcabusApiTools: true },
  addPostAnalysisTags: { needsOrcabusApiTools: true },
  addWesFailureComment: { needsOrcabusApiTools: true },
};

export interface LambdaInput {
  lambdaName: LambdaNameList;
}

export interface LambdaObject extends LambdaInput {
  lambdaFunction: PythonUvFunction;
}
