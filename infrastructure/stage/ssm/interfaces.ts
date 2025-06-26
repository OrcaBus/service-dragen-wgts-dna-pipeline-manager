import { Reference } from '../interfaces';

export interface SsmParameterValues {
  // Payload defaults
  workflowName: string;
  payloadVersion: string;
  workflowVersion: string;

  // Input defaults
  inputsByWorkflowVersionMap: Record<string, object>;

  // Engine Parameter defaults
  pipelineIdsByWorkflowVersionMap: Record<string, string>;
  icav2ProjectId: string;
  logsPrefix: string;
  outputPrefix: string;

  // Reference defaults
  referenceByWorkflowVersionMap: Record<string, Reference>;
  somaticReferenceByWorkflowVersionMap: Record<string, Reference>;
  oraCompressionByWorkflowVersionMap: Record<string, string>;
}

export interface SsmParameterPaths {
  // Top level prefix
  ssmRootPrefix: string;

  // Payload defaults
  workflowName: string;
  payloadVersion: string;
  workflowVersion: string;

  // Input defaults
  prefixDefaultInputsByWorkflowVersion: string;

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

export interface BuildSsmParameterProps {
  ssmParameterValues: SsmParameterValues;
  ssmParameterPaths: SsmParameterPaths;
}
