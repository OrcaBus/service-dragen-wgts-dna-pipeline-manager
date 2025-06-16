import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StatefulApplicationStackConfig } from './interfaces';
import * as ssm from 'aws-cdk-lib/aws-ssm';

export type StatefulApplicationStackProps = StatefulApplicationStackConfig & cdk.StackProps;

export class StatefulApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: StatefulApplicationStackProps) {
    super(scope, id, props);

    /**
     * SSM Stack here
     *
     * */

    /**
     * Detail Level SSM Parameters
     */
    // Workflow name
    new ssm.StringParameter(this, 'workflow-name', {
      parameterName: props.ssmParameterPaths.workflowName,
      stringValue: props.workflowName,
    });

    // Workflow version
    new ssm.StringParameter(this, 'workflow-version', {
      parameterName: props.ssmParameterPaths.workflowVersion,
      stringValue: props.workflowVersion,
    });

    /**
     * Payload level SSM Parameters
     */
    // Payload version
    new ssm.StringParameter(this, 'payload-version', {
      parameterName: props.ssmParameterPaths.payloadVersion,
      stringValue: props.payloadVersion,
    });

    /**
     * Engine Parameters
     */
    // ICAV2 project ID
    new ssm.StringParameter(this, 'icav2-project-id', {
      parameterName: props.ssmParameterPaths.icav2ProjectId,
      stringValue: props.icav2ProjectId,
    });

    // Prefix pipeline IDs by workflow version
    for (const [key, value] of Object.entries(props.pipelineIdsByWorkflowVersionMap)) {
      new ssm.StringParameter(this, `pipeline-id-${key}`, {
        parameterName: `${props.ssmParameterPaths.prefixPipelineIdsByWorkflowVersion}${key}`,
        stringValue: value,
      });
    }

    // Logs Prefix
    new ssm.StringParameter(this, 'logs-prefix', {
      parameterName: props.ssmParameterPaths.logsPrefix,
      stringValue: props.logsPrefix,
    });

    // Output prefix
    new ssm.StringParameter(this, 'output-prefix', {
      parameterName: props.ssmParameterPaths.outputPrefix,
      stringValue: props.outputPrefix,
    });

    /**
     * Reference Parameters
     */
    // Reference by workflow version map
    for (const [key, value] of Object.entries(props.referenceByWorkflowVersionMap)) {
      new ssm.StringParameter(this, `reference-${key}`, {
        parameterName: `${props.ssmParameterPaths.referenceSsmRootPrefix}${key}`,
        stringValue: JSON.stringify(value),
      });
    }

    // Somatic Reference by workflow version map
    for (const [key, value] of Object.entries(props.somaticReferenceByWorkflowVersionMap)) {
      new ssm.StringParameter(this, `somatic-reference-${key}`, {
        parameterName: `${props.ssmParameterPaths.somaticReferenceSsmRootPrefix}${key}`,
        stringValue: JSON.stringify(value),
      });
    }

    // Ora Reference by Ora version map
    for (const [key, value] of Object.entries(props.oraReferenceByOraVersionMap)) {
      new ssm.StringParameter(this, `ora-version-${key}`, {
        parameterName: `${props.ssmParameterPaths.oraCompressionSsmRootPrefix}${key}`,
        stringValue: value,
      });
    }
  }
}
