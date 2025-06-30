import { IEventBus } from 'aws-cdk-lib/aws-events';
import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';

import { LambdaNameList, LambdaObject } from '../lambda/interfaces';
import { SsmParameterPaths } from '../ssm/interfaces';

/**
 * Step Function Interfaces
 */
export type StateMachineNameList =
  // Draft-to-Draft-Complete
  | 'dragenWgtsDnaCompleteDraftSchema'
  // Draft-to-Ready
  | 'dragenWgtsDnaValidateDraftAndPutReadyEvent'
  // Ready-to-Submitted
  | 'dragenWgtsDnaReadyToIcav2WesSubmitted'
  // Post-submission event conversion
  | 'icav2WesEventToWrscEvent';

export const stateMachineNameList: StateMachineNameList[] = [
  // Draft-to-Completed Draft
  'dragenWgtsDnaCompleteDraftSchema',
  // Completed Draft-to-Ready
  'dragenWgtsDnaValidateDraftAndPutReadyEvent',
  // Ready-to-Submitted
  'dragenWgtsDnaReadyToIcav2WesSubmitted',
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
}

export interface StepFunctionObject extends StepFunctionInput {
  sfnObject: StateMachine;
}

export type WireUpPermissionsProps = BuildStepFunctionProps & StepFunctionObject;

export type BuildStepFunctionsProps = Omit<BuildStepFunctionProps, 'stateMachineName'>;

export const stepFunctionsRequirementsMap: Record<StateMachineNameList, StepFunctionRequirements> =
  {
    dragenWgtsDnaCompleteDraftSchema: {
      needsEventPutPermission: true,
      needsSsmParameterStoreAccess: true,
    },
    dragenWgtsDnaValidateDraftAndPutReadyEvent: {
      needsEventPutPermission: true,
    },
    dragenWgtsDnaReadyToIcav2WesSubmitted: {
      needsEventPutPermission: true,
      needsSsmParameterStoreAccess: true,
    },
    icav2WesEventToWrscEvent: {
      needsEventPutPermission: true,
    },
  };

export const stepFunctionToLambdasMap: Record<StateMachineNameList, LambdaNameList[]> = {
  dragenWgtsDnaCompleteDraftSchema: [
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
  dragenWgtsDnaValidateDraftAndPutReadyEvent: ['validateDraftCompleteSchema'],
  dragenWgtsDnaReadyToIcav2WesSubmitted: ['dragenWgtsDnaReadyToIcav2WesRequest'],
  icav2WesEventToWrscEvent: ['convertIcav2WesStateChangeEventToWrscEvent'],
};
