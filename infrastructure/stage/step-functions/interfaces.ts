import { IEventBus } from 'aws-cdk-lib/aws-events';
import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';

import { SsmParameterPaths } from '../interfaces';
import { LambdaNameList, LambdaObject } from '../lambda/interfaces';

/**
 * Step Function Interfaces
 */
export type StateMachineNameList =
  // Draft-to-Ready
  | 'dragenWgtsDnaDraftToReady'
  // Ready-to-Submitted
  | 'dragenWgtsDnaReadyToIcav2WesSubmitted'
  // Post-submission event conversion
  | 'icav2WesEventToWrscEvent';

export const stateMachineNameList: StateMachineNameList[] = [
  // Draft-to-Ready
  'dragenWgtsDnaDraftToReady',
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
    dragenWgtsDnaDraftToReady: {
      needsEventPutPermission: true,
      needsSsmParameterStoreAccess: true,
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
  dragenWgtsDnaDraftToReady: [
    'getMetadataTags',
    'getFastqListRowsFromRgidList',
    'getFastqRgidsFromLibraryId',
    'getFastqSetIdsFromRgidList',
    'getQcSummaryStatsFromRgidList',
    'checkNtsmInternal',
    'checkNtsmExternal',
  ],
  dragenWgtsDnaReadyToIcav2WesSubmitted: ['dragenWgtsDnaReadyToIcav2WesRequest'],
  icav2WesEventToWrscEvent: ['convertIcav2WesStateChangeEventToWrscEvent'],
};
