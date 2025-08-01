import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as events from 'aws-cdk-lib/aws-events';
import { buildAllLambdas } from './lambda';
import { buildAllStepFunctions } from './step-functions';
import { StatelessApplicationStackConfig } from './interfaces';
import { buildAllEventRules } from './event-rules';
import { buildAllEventBridgeTargets } from './event-targets';
import { NagSuppressions } from 'cdk-nag';

export type StatelessApplicationStackProps = cdk.StackProps & StatelessApplicationStackConfig;

export class StatelessApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: StatelessApplicationStackProps) {
    super(scope, id, props);

    /**
     * Dragen WGTS DNA Stack
     * Deploys the Dragen WGTS DNA orchestration services
     */
    // Get the event bus as a construct
    const orcabusMainEventBus = events.EventBus.fromEventBusName(
      this,
      props.eventBusName,
      props.eventBusName
    );

    // Build the lambdas
    const lambdas = buildAllLambdas(this);

    // Build the state mahcines
    const stateMachines = buildAllStepFunctions(this, {
      lambdaObjects: lambdas,
      eventBus: orcabusMainEventBus,
      ssmParameterPaths: props.ssmParameterPaths,
    });

    // Add event rules
    const eventRules = buildAllEventRules(this, {
      eventBus: orcabusMainEventBus,
    });

    // Add event targets
    buildAllEventBridgeTargets({
      eventBridgeRuleObjects: eventRules,
      stepFunctionObjects: stateMachines,
    });

    // Add in Nag Suppressions
    // Suppress IAM4
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason: 'We use the basic execution role for lambda functions',
      },
    ]);
  }
}
