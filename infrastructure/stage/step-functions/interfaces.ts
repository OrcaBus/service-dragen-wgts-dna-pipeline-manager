import { IEventBus } from 'aws-cdk-lib/aws-events';
import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';

import { LambdaNameList, LambdaObject } from '../lambda/interfaces';
import { SsmParameterPaths } from '../ssm/interfaces';

/**
 * Step Function Interfaces
 */
export type StateMachineNameList =
  // Draft-to-Draft-Complete
  | 'populateDraftData'
  // Draft-to-Ready
  | 'validateDraftDataAndPutReadyEvent'
  // Ready-to-Submitted
  | 'readyEventToIcav2WesRequestEvent'
  // Post-submission event conversion
  | 'icav2WesEventToWrscEvent';

export const stateMachineNameList: StateMachineNameList[] = [
  // Draft-to-Completed Draft
  'populateDraftData',
  // Completed Draft-to-Ready
  'validateDraftDataAndPutReadyEvent',
  // Ready-to-Submitted
  'readyEventToIcav2WesRequestEvent',
  // Post-submission event conversion
  'icav2WesEventToWrscEvent',
];

// Requirements interface for Step Functions
export interface StepFunctionRequirements {
  // Event stuff
  needsEventPutPermission?: boolean;

  // SSM Stuff
  needsSsmParameterStoreAccess?: boolean;
}

export interface StepFunctionInput {
  stateMachineName: StateMachineNameList;
}

export interface BuildStepFunctionProps extends StepFunctionInput {
  lambdaObjects: LambdaObject[];
  eventBus: IEventBus;
  ssmParameterPaths: SsmParameterPaths;
  isNewWorkflowManagerDeployed: boolean;
}

export interface StepFunctionObject extends StepFunctionInput {
  sfnObject: StateMachine;
}

export type WireUpPermissionsProps = BuildStepFunctionProps & StepFunctionObject;

export type BuildStepFunctionsProps = Omit<BuildStepFunctionProps, 'stateMachineName'>;

export const stepFunctionsRequirementsMap: Record<StateMachineNameList, StepFunctionRequirements> =
  {
    populateDraftData: {
      needsEventPutPermission: true,
      needsSsmParameterStoreAccess: true,
    },
    validateDraftDataAndPutReadyEvent: {
      needsEventPutPermission: true,
    },
    readyEventToIcav2WesRequestEvent: {
      needsEventPutPermission: true,
    },
    icav2WesEventToWrscEvent: {
      needsEventPutPermission: true,
    },
  };

export const stepFunctionToLambdasMap: Record<StateMachineNameList, LambdaNameList[]> = {
  populateDraftData: [
    'validateDraftCompleteSchema',
    'getLibraries',
    'getMetadataTags',
    'getFastqListRowsFromRgidList',
    'getFastqRgidsFromLibraryId',
    'getFastqIdListFromRgidList',
    'getQcSummaryStatsFromRgidList',
    'checkNtsmInternal',
    'checkNtsmExternal',
  ],
  validateDraftDataAndPutReadyEvent: ['validateDraftCompleteSchema'],
  readyEventToIcav2WesRequestEvent: ['dragenWgtsDnaReadyToIcav2WesRequest'],
  icav2WesEventToWrscEvent: ['convertIcav2WesStateChangeEventToWrscEvent'],
};
