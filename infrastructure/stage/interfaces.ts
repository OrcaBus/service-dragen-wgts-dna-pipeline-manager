/*

Interfaces for the application

 */

import { SsmParameterPaths, SsmParameterValues } from './ssm/interfaces';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';

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

  // Stage Name
  stageName: StageName;

  // Automation service path
  pipelineCacheBucketName: string;
  pipelineCachePrefix: string;
}

export type WorkflowVersionType = '4.4.4' | '4.4.6';

export type PayloadVersionType = '2025.06.04';

export type OraReferenceVersionType = '2.7.0';

/* Consts of types */
export const payloadVersionList: PayloadVersionType[] = ['2025.06.04'];

export interface Reference {
  name: string;
  structure: string;
  tarball: string;
}
