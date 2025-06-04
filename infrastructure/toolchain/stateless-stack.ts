import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { getStackProps } from '../stage/config';
import { REPO_NAME } from './constants';

export class StatelessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatelessDragenWgtsDnaPipeline', {
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatelessStack,
      stackName: 'StatelessDragenWgtsDnaPipelineManager',
      stackConfig: {
        beta: getStackProps('BETA'),
        gamma: getStackProps('GAMMA'),
        prod: getStackProps('PROD'),
      },
      pipelineName: 'OrcaBus-StatelessDragenWgtsDnaPipeline',
      cdkSynthCmd: ['pnpm install --frozen-lockfile --ignore-scripts', 'pnpm cdk-stateless synth'],
    });
  }
}
