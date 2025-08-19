/*

Interfaces for the application

 */

import { SsmParameterPaths, SsmParameterValues } from './ssm/interfaces';

/**
 * Stateful application stack interface.
 */

export interface StatefulApplicationStackConfig {
  // Values
  // Detail
  ssmParameterValues: SsmParameterValues;

  // Keys
  ssmParameterPaths: SsmParameterPaths;
}

/**
 * Stateless application stack interface.
 */
export interface StatelessApplicationStackConfig {
  // SSM Parameter Keys
  ssmParameterPaths: SsmParameterPaths;

  // Event Stuff
  eventBusName: string;

  // Workflow manager stuff
  isNewWorkflowManagerDeployed: boolean;
}

export type WorkflowVersionType = '4.4.4';
export type OraReferenceVersionType = '2.7.0';

export interface Reference {
  name: string;
  structure: string;
  tarball: string;
}
