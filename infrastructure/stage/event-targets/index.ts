import {
  AddSfnAsEventBridgeTargetProps,
  eventBridgeTargetsNameList,
  EventBridgeTargetsProps,
} from './interfaces';
import * as eventsTargets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';

export function buildDragenWgtsDnaDraftToDragenWgtsDnaDraftToReadySfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  // We take in only the event detail from the dragen wgts dna draft event
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildDragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  // We take in the event detail from the dragen wgts dna ready event
  // And return the entire detail to the state machine
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildIcav2WesEventStateChangeToWrscSfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  // We take in the event detail from the icav2 wes state change event
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildAllEventBridgeTargets(scope: Construct, props: EventBridgeTargetsProps) {
  for (const eventBridgeTargetsName of eventBridgeTargetsNameList) {
    switch (eventBridgeTargetsName) {
      case 'dragenWgtsDnaDraftToDraftToReadySfnTarget': {
        buildDragenWgtsDnaDraftToDragenWgtsDnaDraftToReadySfnTarget(<
          AddSfnAsEventBridgeTargetProps
        >{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscDraft'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'dragenWgtsDnaDraftToReady'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget': {
        buildDragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscReady'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'dragenWgtsDnaReadyToIcav2WesSubmitted'
          )?.sfnObject,
        });
        break;
      }
      case 'icav2WesAnalysisStateChangeEventToWrscSfnTarget': {
        buildIcav2WesEventStateChangeToWrscSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) =>
              eventBridgeObject.ruleName === 'dragenWgtsDnaIcav2WesAnalysisStateChange'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'icav2WesEventToWrscEvent'
          )?.sfnObject,
        });
        break;
      }
    }
  }
}
