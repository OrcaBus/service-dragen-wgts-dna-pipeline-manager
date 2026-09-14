import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { REPO_NAME } from './constants';
import { getStatelessStackProps } from '../stage/config';
import { StatelessApplicationStack } from '../stage/stateless-application-stack';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as iam from 'aws-cdk-lib/aws-iam';
import {
  BETA_ENVIRONMENT,
  GAMMA_ENVIRONMENT,
} from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';

export class StatelessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const deploymentPipeline = new DeploymentStackPipeline(this, 'StatelessDragenWgtsDnaPipeline', {
      unitAppTestConfig: {
        command: [],
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

    // Add post-deployment smoke test stages
    this.addSmokeTestStages(deploymentPipeline.pipeline);
  }

  /**
   * Add post-deployment smoke test CodeBuild steps after Beta and Gamma deployment stages.
   *
   * Each smoke test step:
   * - Assumes a cross-account role into the target environment
   * - Discovers deployed Lambda functions and state machines
   * - Performs DryRun invocations and DescribeStateMachine checks
   * - Verifies SSM parameters are accessible
   * - Enforces a 2-minute timeout
   */
  private addSmokeTestStages(pipeline: codepipeline.Pipeline): void {
    // Add smoke tests after Beta deployment
    this.addSmokeTestAction(pipeline, {
      stageName: 'OrcaBusBeta',
      targetAccountId: BETA_ENVIRONMENT.account!,
      targetRegion: BETA_ENVIRONMENT.region!,
      environmentLabel: 'Beta',
    });

    // Add smoke tests after Gamma deployment
    this.addSmokeTestAction(pipeline, {
      stageName: 'OrcaBusGamma',
      targetAccountId: GAMMA_ENVIRONMENT.account!,
      targetRegion: GAMMA_ENVIRONMENT.region!,
      environmentLabel: 'Gamma',
    });
  }

  /**
   * Add a smoke test CodeBuild action to an existing pipeline stage.
   */
  private addSmokeTestAction(
    pipeline: codepipeline.Pipeline,
    config: {
      stageName: string;
      targetAccountId: string;
      targetRegion: string;
      environmentLabel: string;
    }
  ): void {
    // Create IAM role policy for cross-account access
    const smokeTestRoleArn = `arn:aws:iam::${config.targetAccountId}:role/OrcaBus${config.environmentLabel}-CrossAccountSmokeTestRole`;

    // Create the CodeBuild project for smoke tests
    const smokeTestProject = new codebuild.PipelineProject(
      this,
      `SmokeTest${config.environmentLabel}Project`,
      {
        projectName: `OrcaBus-DragenWgtsDna-SmokeTest-${config.environmentLabel}`,
        environment: {
          buildImage: codebuild.LinuxArmBuildImage.AMAZON_LINUX_2023_STANDARD_3_0,
          computeType: codebuild.ComputeType.SMALL,
        },
        timeout: cdk.Duration.minutes(5),
        buildSpec: codebuild.BuildSpec.fromObject({
          version: '0.2',
          phases: {
            install: {
              'runtime-versions': {
                python: '3.14',
              },
              commands: ['pip install boto3 --quiet'],
            },
            build: {
              commands: [
                `python3 smoke-tests/run-smoke-tests.py --role-arn ${smokeTestRoleArn} --region ${config.targetRegion} --stage ${config.environmentLabel} --timeout 120`,
              ],
            },
          },
        }),
      }
    );

    // Grant the CodeBuild project permission to assume the cross-account role
    smokeTestProject.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['sts:AssumeRole'],
        resources: [smokeTestRoleArn],
      })
    );

    // Get the target stage from the pipeline
    const stage = pipeline.stage(config.stageName);

    // Add the smoke test action to the stage
    stage.addAction(
      new codepipeline_actions.CodeBuildAction({
        actionName: `SmokeTest${config.environmentLabel}`,
        project: smokeTestProject,
        input: pipeline.stage('Source').actions[0].actionProperties
          .outputs![0] as codepipeline.Artifact,
        runOrder: 100, // High runOrder ensures this runs after deployment completes
      })
    );
  }
}
