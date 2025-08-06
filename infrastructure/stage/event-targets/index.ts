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
      case 'draftLegacyToCompleteDraftSfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscDraftLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'populateDraftData'
          )?.sfnObject,
        });
        break;
      }
      case 'draftToPopulateDraftSfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscDraft'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'populateDraftData'
          )?.sfnObject,
        });
        break;
      }
      case 'legacyDraftToValidateDraftAndReadySfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscDraftLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'validateDraftDataAndPutReadyEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'draftToValidateDraftAndReadySfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscDraft'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'validateDraftDataAndPutReadyEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'readyLegacyToIcav2WesSubmittedSfnTarget': {
        buildDragenWgtsDnaWrscLegacyToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscReadyLegacy'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'readyEventToIcav2WesRequestEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'readyToIcav2WesSubmittedSfnTarget': {
        buildDragenWgtsDnaWrscToSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'wrscReady'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnObject) => sfnObject.stateMachineName === 'readyEventToIcav2WesRequestEvent'
          )?.sfnObject,
        });
        break;
      }
      case 'icav2WesAnalysisStateChangeEventToWrscSfnTarget': {
        buildIcav2WesEventStateChangeToWrscSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'icav2WesAnalysisStateChange'
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
