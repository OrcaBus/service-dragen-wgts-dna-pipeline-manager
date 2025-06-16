import { LambdaInput, lambdaNameList, LambdaObject, lambdaRequirementsMap } from './interfaces';
import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import { LAMBDA_DIR, WORKFLOW_NAME, DEFAULT_WORKFLOW_VERSION } from '../constants';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';
import { camelCaseToSnakeCase } from '../utils';
import * as path from 'path';
// import { ICommandHooks } from '@aws-cdk/aws-lambda-python-alpha';

function buildLambda(scope: Construct, props: LambdaInput): LambdaObject {
  const lambdaNameToSnakeCase = camelCaseToSnakeCase(props.lambdaName);
  const lambdaRequirements = lambdaRequirementsMap[props.lambdaName];

  // Set command hooks
  // let commandHooks: ICommandHooks = {
  //   // eslint-disable-next-line @typescript-eslint/no-unused-vars
  //   beforeBundling(inputDir: string, outputDir: string): string[] {
  //     return [];
  //   },
  //   // eslint-disable-next-line @typescript-eslint/no-unused-vars
  //   afterBundling: function (inputDir: string, outputDir: string): string[] {
  //     return [];
  //   },
  // };
  // if (props.lambdaName === 'validateDragenWgtsDnaWrscReady') {
  //   commandHooks = {
  //     beforeBundling(inputDir: string, outputDir: string): string[] {
  //       return [
  //         `cp ${path.join(inputDir, '../../event-schemas/dragen-wgts-dna-wrsc-ready-schema.json')} ${outputDir}`,
  //       ];
  //     },
  //     // eslint-disable-next-line @typescript-eslint/no-unused-vars
  //     afterBundling: function (inputDir: string, outputDir: string): string[] {
  //       return [];
  //     },
  //   };
  // }

  // Create the lambda function
  const lambdaFunction = new PythonUvFunction(scope, props.lambdaName, {
    entry: path.join(LAMBDA_DIR, lambdaNameToSnakeCase + '_py'),
    runtime: lambda.Runtime.PYTHON_3_12,
    architecture: lambda.Architecture.ARM_64,
    index: lambdaNameToSnakeCase + '.py',
    handler: 'handler',
    timeout: Duration.seconds(60),
    memorySize: 2048,
    includeOrcabusApiToolsLayer: lambdaRequirements.needsOrcabusApiTools,
  });

  // AwsSolutions-L1 - We'll migrate to PYTHON_3_13 ASAP, soz
  // AwsSolutions-IAM4 - We need to add this for the lambda to work
  NagSuppressions.addResourceSuppressions(
    lambdaFunction,
    [
      {
        id: 'AwsSolutions-L1',
        reason: 'Will migrate to PYTHON_3_13 ASAP, soz',
      },
    ],
    true
  );

  /*
    Special if the lambdaName is 'generateWorkflowRunNameAndPortalRunId'
    We need to add a specific environment variable for this lambda
     */
  if (props.lambdaName === 'generateWorkflowRunNameAndPortalRunId') {
    lambdaFunction.addEnvironment('WORKFLOW_NAME', WORKFLOW_NAME);
    lambdaFunction.addEnvironment('WORKFLOW_VERSION', DEFAULT_WORKFLOW_VERSION);
  }

  /* Return the function */
  return {
    lambdaName: props.lambdaName,
    lambdaFunction: lambdaFunction,
  };
}

export function buildAllLambdas(scope: Construct): LambdaObject[] {
  // Iterate over lambdaLayerToMapping and create the lambda functions
  const lambdaObjects: LambdaObject[] = [];
  for (const lambdaName of lambdaNameList) {
    lambdaObjects.push(
      buildLambda(scope, {
        lambdaName: lambdaName,
      })
    );
  }

  return lambdaObjects;
}
