import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as events from 'aws-cdk-lib/aws-events';
import { buildAllLambdas } from './lambda';
import { buildAllStepFunctions } from './step-functions';
import { StatelessApplicationStackConfig } from './interfaces';
import { buildAllEventRules } from './event-rules';
import { buildAllEventBridgeTargets } from './event-targets';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';

export type StatelessApplicationStackProps = cdk.StackProps & StatelessApplicationStackConfig;

export class StatelessApplicationStack extends cdk.Stack {
  public readonly stageName: StageName;

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

    // Set the stage name
    this.stageName = props.stageName;

    // Build the lambdas
    const lambdas = buildAllLambdas(this);

    // Build the state machines
    const stateMachines = buildAllStepFunctions(this, {
      lambdaObjects: lambdas,
      eventBus: orcabusMainEventBus,
      ssmParameterPaths: props.ssmParameterPaths,
      isNewWorkflowManagerDeployed: props.isNewWorkflowManagerDeployed,
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
  }
}
