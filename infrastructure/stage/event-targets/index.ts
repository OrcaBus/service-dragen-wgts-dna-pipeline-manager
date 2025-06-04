import {
  AddSfnAsEventBridgeTargetProps,
  eventBridgeTargetsNameList,
  EventBridgeTargetsProps,
} from './interfaces';
import * as eventsTargets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import { EventField, RuleTargetInput } from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';

export function buildBsshFastqCopySucceededTodragenWgtsDnaReadySfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  // We take in the event detail from the bssh fastq copy succeeded event
  // And return only the instrument run id and the output prefix and linkedLibraries
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: RuleTargetInput.fromObject({
        instrumentRunId: EventField.fromPath('$.detail.payload.data.outputs.instrumentRunId'),
        primaryDataOutputUri: EventField.fromPath('$.detail.payload.data.outputs.outputUri'),
        linkedLibraries: EventField.fromPath('$.detail.linkedLibraries'),
      }),
    })
  );
}

export function builddragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  // We take in the event detail from the bssh fastq copy succeeded event
  // And return only the instrument run id and the output prefix and linkedLibraries
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
  // And return only the instrument run id and the output prefix and linkedLibraries
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildAllEventBridgeTargets(scope: Construct, props: EventBridgeTargetsProps) {
  for (const eventBridgeTargetsName of eventBridgeTargetsNameList) {
    switch (eventBridgeTargetsName) {
      case 'dragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget': {
        builddragenWgtsDnaReadyToIcav2WesSubmittedSfnTarget(<AddSfnAsEventBridgeTargetProps>{
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (eventBridgeObject) => eventBridgeObject.ruleName === 'dragenWgtsDnaWrscReady'
          )?.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (eventBridgeObject) =>
              eventBridgeObject.stateMachineName === 'dragenWgtsDnaReadyToIcav2WesSubmitted'
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
            (eventBridgeObject) => eventBridgeObject.stateMachineName === 'icav2WesEventToWrscEvent'
          )?.sfnObject,
        });
        break;
      }
    }
  }
}
