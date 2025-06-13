import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';

/**
 * Lambda function interface.
 */
export type LambdaNameList =
  | 'dragenWgtsDnaReadyToIcav2WesRequest'
  | 'convertIcav2WesStateChangeEventToWrscEvent'
  | 'generateWorkflowRunNameAndPortalRunId'
  | 'validateDragenWgtsDnaWrscReady';

export const lambdaNameList: LambdaNameList[] = [
  'dragenWgtsDnaReadyToIcav2WesRequest',
  'convertIcav2WesStateChangeEventToWrscEvent',
  'generateWorkflowRunNameAndPortalRunId',
];

// Requirements interface for Lambda functions
export interface LambdaRequirements {
  needsOrcabusApiTools?: boolean;
}

// Lambda requirements mapping
export const lambdaRequirementsMap: Record<LambdaNameList, LambdaRequirements> = {
  dragenWgtsDnaReadyToIcav2WesRequest: {},
  // Needs Orcabus API tools to fetch the existing workflow run state
  convertIcav2WesStateChangeEventToWrscEvent: { needsOrcabusApiTools: true },
  // Needs Orcabus API tools to generate the workflow run name and portal run ID
  generateWorkflowRunNameAndPortalRunId: { needsOrcabusApiTools: true },
  validateDragenWgtsDnaWrscReady: { needsOrcabusApiTools: false },
};

export interface LambdaInput {
  lambdaName: LambdaNameList;
}

export interface LambdaObject extends LambdaInput {
  lambdaFunction: PythonUvFunction;
}
