import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';
import { Rule } from 'aws-cdk-lib/aws-events';
import { EventBridgeRuleObject } from '../event-rules/interfaces';
import { StepFunctionObject } from '../step-functions/interfaces';

/**
 * EventBridge Target Interfaces
 */
export type EventBridgeTargetName =
  // Draft to Ready State Machine Targets
  | 'draftToPopulateDraftSfnTarget'
  | 'draftToValidateDraftAndReadySfnTarget'
  // Ready to WES State Machine Targets
  | 'readyToIcav2WesSubmittedSfnTarget'
  // WES Analysis State Change Event to WRSC State Machine Target
  | 'icav2WesAnalysisStateChangeEventToWrscSfnTarget';

export const eventBridgeTargetsNameList: EventBridgeTargetName[] = [
  // Draft to Ready State Machine Targets
  'draftToPopulateDraftSfnTarget',
  'draftToValidateDraftAndReadySfnTarget',
  // Ready to WES State Machine Targets
  'readyToIcav2WesSubmittedSfnTarget',
  // WES Analysis State Change Event to WRSC State Machine Target
  'icav2WesAnalysisStateChangeEventToWrscSfnTarget',
];

export interface AddSfnAsEventBridgeTargetProps {
  stateMachineObj: StateMachine;
  eventBridgeRuleObj: Rule;
}

export interface EventBridgeTargetsProps {
  eventBridgeRuleObjects: EventBridgeRuleObject[];
  stepFunctionObjects: StepFunctionObject[];
}
