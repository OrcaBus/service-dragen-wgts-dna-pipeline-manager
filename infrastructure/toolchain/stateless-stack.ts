import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { REPO_NAME } from './constants';
import { getStatelessStackProps } from '../stage/config';
import { StatelessApplicationStack } from '../stage/stateless-application-stack';

export class StatelessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatelessDragenWgtsDnaPipeline', {
      unitAppTestConfig: {
        command: [
          // Install Python test dependencies
          'python3.14 -m pip install -r app/tests/requirements-test.txt --quiet',
          // Run Lambda unit tests
          'python3.14 -m pytest app/lambdas/tests/ -v --tb=short',
          // Run ASL validation
          'python3.14 -m pytest app/step-functions-templates/tests/test_asl_validation.py -v --tb=short',
        ],
      },
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatelessApplicationStack,
      stackName: 'StatelessDragenWgtsDnaPipelineManager',
      stackConfig: {
        beta: getStatelessStackProps('BETA'),
        gamma: getStatelessStackProps('GAMMA'),
        prod: getStatelessStackProps('PROD'),
      },
      pipelineName: 'OrcaBus-StatelessDragenWgtsDnaPipeline',
      cdkSynthCmd: ['pnpm install --frozen-lockfile --ignore-scripts', 'pnpm cdk-stateless synth'],
      enableSlackNotification: false,
    });
  }
}
