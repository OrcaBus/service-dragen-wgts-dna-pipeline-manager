/*

Interfaces for the application

 */

/**
 * Stateful application stack interface.
 */

export interface SsmParameterPaths {
  ssmRootPrefix: string;
  workflowName: string;
  workflowVersion: string;
  prefixPipelineIdsByWorkflowVersion: string;
  icav2ProjectId: string;
  payloadVersion: string;
  logsPrefix: string;
  outputPrefix: string;
}

export interface StatefulApplicationStackConfig {
  // Values
  workflowName: string;
  workflowVersion: string;
  pipelineIdsByWorkflowVersionMap: Record<string, string>;
  icav2ProjectId: string;
  payloadVersion: string;
  logsPrefix: string;
  outputPrefix: string;
  // Keys
  ssmParameterPaths: SsmParameterPaths;
}

/**
 * Stateless application stack interface.
 */
export interface StatelessApplicationStackConfig {
  // SSM Parameter Keys
  ssmParameterPaths: SsmParameterPaths;

  // We need the workflow name though for the event rules
  workflowName: string;

  // Event Stuff
  eventBusName: string;
  eventSource: string;
  workflowRunStateChangeDetailType: string;
  icav2WesRequestDetailType: string;
  icav2WesStateChangeDetailType: string;
}
