/** Step Function stuff */
import {
  BuildStepFunctionProps,
  BuildStepFunctionsProps,
  stateMachineNameList,
  StepFunctionObject,
  stepFunctionsRequirementsMap,
  stepFunctionToLambdasMap,
  WireUpPermissionsProps,
} from './interfaces';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cdk from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import path from 'path';
import {
  DEFAULT_ORA_VERSION,
  EVENT_SOURCE,
  FASTQ_SYNC_DETAIL_TYPE,
  ICAV2_WES_REQUEST_DETAIL_TYPE,
  READY_STATUS,
  STEP_FUNCTIONS_DIR,
  WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE,
} from '../constants';
import { Construct } from 'constructs';
import { camelCaseToSnakeCase } from '../utils';

function createStateMachineDefinitionSubstitutions(props: BuildStepFunctionProps): {
  [key: string]: string;
} {
  const definitionSubstitutions: { [key: string]: string } = {};

  const sfnRequirements = stepFunctionsRequirementsMap[props.stateMachineName];
  const lambdaFunctionNamesInSfn = stepFunctionToLambdasMap[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );

  /* Substitute lambdas in the state machine definition */
  for (const lambdaObject of lambdaFunctions) {
    const sfnSubtitutionKey = `__${camelCaseToSnakeCase(lambdaObject.lambdaName)}_lambda_function_arn__`;
    definitionSubstitutions[sfnSubtitutionKey] =
      lambdaObject.lambdaFunction.currentVersion.functionArn;
  }

  /* Sfn Requirements */
  if (sfnRequirements.needsEventPutPermission) {
    definitionSubstitutions['__event_bus_name__'] = props.eventBus.eventBusName;
    definitionSubstitutions['__workflow_run_state_change_event_detail_type__'] =
      WORKFLOW_RUN_STATE_CHANGE_DETAIL_TYPE;
    definitionSubstitutions['__event_source__'] = EVENT_SOURCE;
    definitionSubstitutions['__icav2_wes_request_detail_type__'] = ICAV2_WES_REQUEST_DETAIL_TYPE;
    definitionSubstitutions['__fastq_sync_detail_type__'] = FASTQ_SYNC_DETAIL_TYPE;
    definitionSubstitutions['__stack_source__'] = EVENT_SOURCE;
    definitionSubstitutions['__ready_event_status__'] = READY_STATUS;
  }

  if (sfnRequirements.needsSsmParameterStoreAccess) {
    definitionSubstitutions['__default_project_id_ssm_parameter_name__'] =
      props.ssmParameterPaths.icav2ProjectId;
    definitionSubstitutions['__workflow_name_ssm_parameter_name__'] =
      props.ssmParameterPaths.workflowName; // Not currently used
    definitionSubstitutions['__workflow_version_ssm_parameter_name__'] =
      props.ssmParameterPaths.workflowVersion; // Not currently used
    definitionSubstitutions['__default_output_uri_prefix_ssm_parameter_name__'] =
      props.ssmParameterPaths.outputPrefix;
    definitionSubstitutions['__default_logs_uri_prefix_ssm_parameter_name__'] =
      props.ssmParameterPaths.logsPrefix;
    // Path to mapping workflow version to ICAv2 Pipeline ID
    definitionSubstitutions['__workflow_id_to_pipeline_id_ssm_parameter_path_prefix__'] =
      props.ssmParameterPaths.prefixPipelineIdsByWorkflowVersion;
    // Reference SSM prefixes
    definitionSubstitutions['__default_reference_ssm_parameter_prefix__'] =
      props.ssmParameterPaths.referenceSsmRootPrefix;
    definitionSubstitutions['__default_somatic_reference_ssm_parameter_prefix__'] =
      props.ssmParameterPaths.somaticReferenceSsmRootPrefix;
    definitionSubstitutions['__default_ora_reference_ssm_parameter_prefix__'] =
      props.ssmParameterPaths.oraCompressionSsmRootPrefix;
    definitionSubstitutions['__default_ora_version__'] = DEFAULT_ORA_VERSION;
  }

  return definitionSubstitutions;
}

function wireUpStateMachinePermissions(props: WireUpPermissionsProps): void {
  /* Wire up lambda permissions */
  const sfnRequirements = stepFunctionsRequirementsMap[props.stateMachineName];

  const lambdaFunctionNamesInSfn = stepFunctionToLambdasMap[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );

  if (sfnRequirements.needsEventPutPermission) {
    props.eventBus.grantPutEventsTo(props.sfnObject);
  }

  if (sfnRequirements.needsSsmParameterStoreAccess) {
    // We give access to the full prefix
    // At the cost of needing a nag suppression
    props.sfnObject.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:parameter${props.ssmParameterPaths.ssmRootPrefix}*`,
        ],
      })
    );

    NagSuppressions.addResourceSuppressions(
      props.sfnObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'We need to give access to the full prefix for the SSM parameter store',
        },
      ],
      true
    );
  }

  /* Allow the state machine to invoke the lambda function */
  for (const lambdaObject of lambdaFunctions) {
    lambdaObject.lambdaFunction.currentVersion.grantInvoke(props.sfnObject);
  }
}

function buildStepFunction(scope: Construct, props: BuildStepFunctionProps): StepFunctionObject {
  const sfnNameToSnakeCase = camelCaseToSnakeCase(props.stateMachineName);

  /* Create the state machine definition substitutions */
  const stateMachine = new sfn.StateMachine(scope, props.stateMachineName, {
    stateMachineName: `dragen-wgts-dna-${props.stateMachineName}`,
    definitionBody: sfn.DefinitionBody.fromFile(
      path.join(STEP_FUNCTIONS_DIR, sfnNameToSnakeCase + `_sfn_template.asl.json`)
    ),
    definitionSubstitutions: createStateMachineDefinitionSubstitutions(props),
  });

  /* Grant the state machine permissions */
  wireUpStateMachinePermissions({
    sfnObject: stateMachine,
    ...props,
  });

  /* Nag Suppressions */
  /* AwsSolutions-SF1 - We don't need ALL events to be logged */
  /* AwsSolutions-SF2 - We also don't need X-Ray tracing */
  NagSuppressions.addResourceSuppressions(
    stateMachine,
    [
      {
        id: 'AwsSolutions-SF1',
        reason: 'We do not need all events to be logged',
      },
      {
        id: 'AwsSolutions-SF2',
        reason: 'We do not need X-Ray tracing',
      },
    ],
    true
  );

  /* Return as a state machine object property */
  return {
    ...props,
    sfnObject: stateMachine,
  };
}

export function buildAllStepFunctions(
  scope: Construct,
  props: BuildStepFunctionsProps
): StepFunctionObject[] {
  const stepFunctionObjects: StepFunctionObject[] = [];

  for (const stepFunctionName of stateMachineNameList) {
    stepFunctionObjects.push(
      buildStepFunction(scope, {
        stateMachineName: stepFunctionName,
        lambdaObjects: props.lambdaObjects,
        eventBus: props.eventBus,
        ssmParameterPaths: props.ssmParameterPaths,
      })
    );
  }

  return stepFunctionObjects;
}
