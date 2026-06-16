import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StatefulApplicationStackConfig } from './interfaces';
import { buildSchemas } from './event-schemas';
import { buildSsmParameters } from './ssm';
import { GitStack } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';

export type StatefulApplicationStackProps = StatefulApplicationStackConfig & cdk.StackProps;

export class StatefulApplicationStack extends GitStack {
  constructor(scope: Construct, id: string, props: StatefulApplicationStackProps) {
    super(scope, id, props);

    // Build SSM Parameters
    buildSsmParameters(this, {
      ssmParameterPaths: props.ssmParameterPaths,
      ssmParameterValues: props.ssmParameterValues,
    });

    // Build Schema stack
    buildSchemas(this);
  }
}
