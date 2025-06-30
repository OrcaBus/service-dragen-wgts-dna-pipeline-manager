import { LambdaInput, lambdaNameList, LambdaObject, lambdaRequirementsMap } from './interfaces';
import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import {
  LAMBDA_DIR,
  WORKFLOW_NAME,
  DEFAULT_WORKFLOW_VERSION,
  SCHEMA_REGISTRY_NAME,
  SSM_SCHEMA_ROOT,
} from '../constants';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';
import { camelCaseToKebabCase, camelCaseToSnakeCase } from '../utils';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import * as iam from 'aws-cdk-lib/aws-iam';
import { SchemaNamesList } from '../event-schemas/interfaces';

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
    Add in SSM permissions for the lambda function
    */
  if (lambdaRequirements.needsSsmParametersAccess) {
    lambdaFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:parameter${SSM_SCHEMA_ROOT}/*`,
        ],
      })
    );
  }

  /*
    For the schema validation lambdas we need to give them the access to the schema
    */
  if (lambdaRequirements.needsSchemaRegistryAccess) {
    // Add the schema registry access to the lambda function
    lambdaFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['schemas:DescribeRegistry', 'schemas:DescribeSchema'],
        resources: [
          `arn:aws:schemas:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:registry/${SCHEMA_REGISTRY_NAME}`,
          `arn:aws:schemas:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:schema/${SCHEMA_REGISTRY_NAME}/*`,
        ],
      })
    );

    /* Since we dont ask which schema, we give the lambda access to all schemas in the registry */
    /* As such we need to add the wildcard to the resource */
    NagSuppressions.addResourceSuppressions(
      lambdaFunction,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'We need to give the lambda access to all schemas in the registry',
        },
      ],
      true
    );
  }

  /*
    Special if the lambdaName is 'generateWorkflowRunNameAndPortalRunId'
    We need to add a specific environment variable for this lambda
     */
  if (props.lambdaName === 'generateWorkflowRunNameAndPortalRunId') {
    lambdaFunction.addEnvironment('WORKFLOW_NAME', WORKFLOW_NAME);
    lambdaFunction.addEnvironment('WORKFLOW_VERSION', DEFAULT_WORKFLOW_VERSION);
  }

  /*
    Special if the lambdaName is 'validateDraftCompleteSchema', we need to add in the ssm parameters
    to the REGISTRY_NAME and SCHEMA_NAME
   */
  if (props.lambdaName === 'validateDraftCompleteSchema') {
    const draftSchemaName: SchemaNamesList = 'dragenWgtsDnaCompleteDataDraft';
    lambdaFunction.addEnvironment('SSM_REGISTRY_NAME', path.join(SSM_SCHEMA_ROOT, 'registry'));
    lambdaFunction.addEnvironment(
      'SSM_SCHEMA_NAME',
      path.join(SSM_SCHEMA_ROOT, camelCaseToKebabCase(draftSchemaName), 'latest')
    );
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
