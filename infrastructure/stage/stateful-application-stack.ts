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

    // Workflow name
    new ssm.StringParameter(this, props.workflowName, {
      parameterName: props.ssmParameterPaths.workflowName,
      stringValue: props.workflowName,
    });

    // Workflow version
    new ssm.StringParameter(this, props.workflowVersion, {
      parameterName: props.ssmParameterPaths.workflowVersion,
      stringValue: props.workflowVersion,
    });

    // Prefix pipeline IDs by workflow version
    for (const [key, value] of Object.entries(props.pipelineIdsByWorkflowVersionMap)) {
      new ssm.StringParameter(this, `${props.workflowName}-${key}`, {
        parameterName: `${props.ssmParameterPaths.prefixPipelineIdsByWorkflowVersion}${key}`,
        stringValue: value,
      });
    }

    // ICAV2 project ID
    new ssm.StringParameter(this, props.icav2ProjectId, {
      parameterName: props.ssmParameterPaths.icav2ProjectId,
      stringValue: props.icav2ProjectId,
    });

    // Payload version
    new ssm.StringParameter(this, props.payloadVersion, {
      parameterName: props.ssmParameterPaths.payloadVersion,
      stringValue: props.payloadVersion,
    });

    // Logs Prefix
    new ssm.StringParameter(this, props.logsPrefix, {
      parameterName: props.ssmParameterPaths.logsPrefix,
      stringValue: props.logsPrefix,
    });

    // Output prefix
    new ssm.StringParameter(this, props.outputPrefix, {
      parameterName: props.ssmParameterPaths.outputPrefix,
      stringValue: props.outputPrefix,
    });
  }
}
