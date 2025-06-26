import {
  AddSfnAsEventBridgeTargetProps,
  eventBridgeTargetsNameList,
  EventBridgeTargetsProps,
} from './interfaces';
import * as eventsTargets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import { EventField } from 'aws-cdk-lib/aws-events';

export function buildDragenWgtsDnaWrscLegacyToSfnTarget(props: AddSfnAsEventBridgeTargetProps) {
  // We take in the event detail from the dragen wgts dna ready event
  // And return the entire detail to the state machine
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromObject({
        status: EventField.fromPath('$.detail.status'),
        timestamp: EventField.fromPath('$.detail.timestamp'),
        workflow: {
          name: EventField.fromPath('$.detail.workflowName'),
          version: EventField.fromPath('$.detail.workflowVersion'),
        },
        workflowRunName: EventField.fromPath('$.detail.workflowRunName'),
        portalRunId: EventField.fromPath('$.detail.portalRunId'),
        libraries: EventField.fromPath('$.detail.linkedLibraries'),
        payload: EventField.fromPath('$.detail.payload'),
      }),
    })
  );
}

export function buildDragenWgtsDnaWrscToSfnTarget(props: AddSfnAsEventBridgeTargetProps) {
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

export function buildAllEventBridgeTargets(props: EventBridgeTargetsProps) {
  for (const eventBridgeTargetsName of eventBridgeTargetsNameList) {
    switch (eventBridgeTargetsName) {
      case 'dragenWgtsDnaDraftLegacyToCompleteDraftSfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscDraftLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'dragenWgtsDnaCompleteDraftSchema'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaDraftToCompleteDraftSfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscDraft'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'dragenWgtsDnaCompleteDraftSchema'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaDraftLegacyToValidateDraftAndReadySfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscDraftLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) =>
              sfnObject.stateMachineName === 'dragenWgtsDnaValidateDraftAndPutReadyEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaDraftToValidateDraftAndReadySfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscDraft'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) =>
              sfnObject.stateMachineName === 'dragenWgtsDnaValidateDraftAndPutReadyEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaReadyLegacyToIcav2WesSubmittedSfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscReadyLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'dragenWgtsDnaReadyToIcav2WesSubmitted'
          )?.sfnObject,
        });
        break;
      }
      case 'dragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
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
