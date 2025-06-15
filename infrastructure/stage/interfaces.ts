/*

Interfaces for the application

 */

/**
 * Stateful application stack interface.
 */

export interface SsmParameterPaths {
  // Top level prefix
  ssmRootPrefix: string;

  // Payload defaults
  workflowName: string;
  payloadVersion: string;
  workflowVersion: string;

  // Engine Parameter defaults
  prefixPipelineIdsByWorkflowVersion: string;
  icav2ProjectId: string;
  logsPrefix: string;
  outputPrefix: string;

  // Reference defaults
  referenceSsmRootPrefix: string;
  somaticReferenceSsmRootPrefix: string;
  oraCompressionSsmRootPrefix: string;
}

export interface StatefulApplicationStackConfig {
  // Values
  // Detail
  workflowName: string;
  workflowVersion: string;

  // Payload
  payloadVersion: string;

  // Engine Parameters
  pipelineIdsByWorkflowVersionMap: Record<string, string>;
  icav2ProjectId: string;
  logsPrefix: string;
  outputPrefix: string;

  // Reference maps
  referenceByWorkflowVersionMap: Record<string, Reference>;
  somaticReferenceByWorkflowVersionMap: Record<string, Reference>;
  oraReferenceByOraVersionMap: Record<string, string>;

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

export interface Reference {
  name: string;
  structure: string;
  tarball: string;
}
