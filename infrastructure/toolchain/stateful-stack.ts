import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { getStackProps } from '../stage/config';
import { REPO_NAME } from './constants';

export class StatefulStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatefulDragenWgtsDnaPipeline', {
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatefulStack,
      stackName: 'StatefulDragenWgtsDnaPipeline',
      stackConfig: {
        beta: getStackProps('BETA'),
        gamma: getStackProps('GAMMA'),
        prod: getStackProps('PROD'),
      },
      pipelineName: 'OrcaBus-StatefulDragenWgtsDnaPipeline',
      cdkSynthCmd: ['pnpm install --frozen-lockfile --ignore-scripts', 'pnpm cdk-stateful synth'],
    });
  }
}
