import { Construct } from 'constructs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { BuildSsmParameterProps } from './interfaces';

import * as path from 'path';

export function buildSsmParameters(scope: Construct, props: BuildSsmParameterProps) {
  /**
   * SSM Stack here
   *
   * */

  /**
   * Detail Level SSM Parameters
   */
  // Workflow name
  new ssm.StringParameter(scope, 'workflow-name', {
    parameterName: props.ssmParameterPaths.workflowName,
    stringValue: props.ssmParameterValues.workflowName,
  });

  // Workflow version
  new ssm.StringParameter(scope, 'workflow-version', {
    parameterName: props.ssmParameterPaths.workflowVersion,
    stringValue: props.ssmParameterValues.workflowVersion,
  });

  /**
   * Payload level SSM Parameters
   */
  // Payload version
  new ssm.StringParameter(scope, 'payload-version', {
    parameterName: props.ssmParameterPaths.payloadVersion,
    stringValue: props.ssmParameterValues.payloadVersion,
  });

  /**
   * Default input SSM Parameters
   */
  // Default inputs by version map
  for (const [key, value] of Object.entries(props.ssmParameterValues.inputsByWorkflowVersionMap)) {
    new ssm.StringParameter(scope, `inputs-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.prefixDefaultInputsByWorkflowVersion, key),
      stringValue: JSON.stringify(value),
    });
  }

  /**
   * Engine Parameters
   */
  // ICAV2 project ID
  new ssm.StringParameter(scope, 'icav2-project-id', {
    parameterName: props.ssmParameterPaths.icav2ProjectId,
    stringValue: props.ssmParameterValues.icav2ProjectId,
  });

  // Prefix pipeline IDs by workflow version
  for (const [key, value] of Object.entries(
    props.ssmParameterValues.pipelineIdsByWorkflowVersionMap
  )) {
    new ssm.StringParameter(scope, `pipeline-id-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.prefixPipelineIdsByWorkflowVersion, key),
      stringValue: value,
    });
  }

  // Logs Prefix
  new ssm.StringParameter(scope, 'logs-prefix', {
    parameterName: props.ssmParameterPaths.logsPrefix,
    stringValue: props.ssmParameterValues.logsPrefix,
  });

  // Output prefix
  new ssm.StringParameter(scope, 'output-prefix', {
    parameterName: props.ssmParameterPaths.outputPrefix,
    stringValue: props.ssmParameterValues.outputPrefix,
  });

  /**
   * Reference Parameters
   */

  // Reference by workflow version map
  for (const [key, value] of Object.entries(
    props.ssmParameterValues.referenceByWorkflowVersionMap
  )) {
    new ssm.StringParameter(scope, `reference-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.referenceSsmRootPrefix, key),
      stringValue: JSON.stringify(value),
    });
  }

  // Somatic Reference by workflow version map
  for (const [key, value] of Object.entries(
    props.ssmParameterValues.somaticReferenceByWorkflowVersionMap
  )) {
    new ssm.StringParameter(scope, `somatic-reference-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.somaticReferenceSsmRootPrefix, key),
      stringValue: JSON.stringify(value),
    });
  }

  // Ora Reference by Ora version map
  for (const [key, value] of Object.entries(
    props.ssmParameterValues.oraCompressionByWorkflowVersionMap
  )) {
    new ssm.StringParameter(scope, `ora-version-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.oraCompressionSsmRootPrefix, key),
      stringValue: value,
    });
  }
}
