Dragen WGTS DNA Pipeline Manager
================================================================================

- [Description](#description)
  - [Summary](#summary)
  - [Events Overview](#events-overview)
  - [Consumed Events](#consumed-events)
  - [Published Events](#published-events)
  - [DRAFT Event Examples](#draft-event-examples)
    - [Minimal DRAFT event example](#minimal-draft-event-example)
    - [Complete DRAFT event example](#complete-draft-event-example)
    - [Manually Validating Schemas,](#manually-validating-schemas)
    - [Making your own DRAFT WRU events with BASH / JQ (new system)](#making-your-own-draft-wru-events-with-bash--jq-new-system)
    - [Making your own DRAFT WRSC events with BASH / JQ (legacy system)](#making-your-own-draft-wrsc-events-with-bash--jq-legacy-system)
    - [Release management](#release-management)
- [Infrastructure \& Deployment](#infrastructure--deployment)
  - [Stateful Stack](#stateful-stack)
  - [Stateless Stack](#stateless-stack)
    - [Step Functions](#step-functions)
  - [CDK Commands](#cdk-commands)
  - [Stacks](#stacks)
    - [Stateful Stack](#stateful-stack-1)
    - [Stateless Stack](#stateless-stack-1)
- [Development](#development)
  - [Project Structure :construct:](#project-structure-construct)
  - [Setup](#setup)
    - [Requirements](#requirements)
    - [Install Dependencies](#install-dependencies)
    - [Update Dependencies](#update-dependencies)
  - [Conventions](#conventions)
  - [Linting \& Formatting](#linting--formatting)
  - [Testing](#testing)
- [Glossary \& References](#glossary--references)

Description
--------------------------------------------------------------------------------

### Summary

This is the Dragen WGTS DNA Pipeline Management service,
responsible for managing the Dragen WGTS DNA pipeline.

This service has 3 parts:
- **DRAFT Event Populator**: responsible for providing execution parameters
- **DRAFT Event Validator**: responsible for validating execution requirements
- **Execution Manager**: responsible for executing and monitoring pipeline runs
  - **ICAv2 WES to WRU Converter**: (sub-component) responsible for converting external WES events to internal WRU events

The pipeline itself runs on ICAv2 through CWL

### Events Overview

![events-overview](docs/drawio-exports/dragen-wgts-dna.drawio.svg)

**DRAFT Event Population**
This is handled by the DRAFT Event Populator.
We listen to DRAFT WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We then try to populate the inputs for the workflow run, and generate a complete DRAFT WRU event.

**DRAFT Event Validation**
This is handled by the DRAFT Event Validator.
We listen to DRAFT WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We then validate the DRAFT event against the schema, and if valid, we generate a READY WRU event.

**READY Event Handler**
This is handled by the Execution Manager.
We listen to READY WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We parse this to the ICAv2 WES Service to generate a ICAv2 WES workflow request.

**ICAv2 WES Analysis State Change**
This is handled by the Execution Manager.
We then parse `Icav2WesAnalysisStateChange` events from the ICAv2 WES Service to update the state of the workflow in our service and forward any changes as WRU events.

### Consumed Events

| Name / DetailType             | Source             | Schema Link   | Description                           |
|-------------------------------|--------------------|---------------|---------------------------------------|
| `WorkflowRunStateChange`      | `orcabus.workflowmanager` | [WorkflowRunStateChange](https://github.com/OrcaBus/wiki/tree/main/orcabus-platform#workflowrunstatechange) | Source of updates on WorkflowRuns (expected pipeline executions) |
| `Icav2WesAnalysisStateChange` | `orcabus.icav2wes` | TODO | ICAv2 WES Analysis State Change event |

### Published Events

| Name / DetailType        | Source                  | Schema Link   | Description           |
|--------------------------|-------------------------|---------------|-----------------------|
| `WorkflowRunUpdate`      | `orcabus.dragenwgtsdna` | [WorkflowRunUpdate](https://github.com/OrcaBus/wiki/tree/main/orcabus-platform#workflowrunupdate) | Reporting any updates to the pipeline state |

### DRAFT Event Examples

#### Minimal DRAFT event example

<details>

<summary>Click to expand</summary>

```json5
{
  "EventBusName": "OrcaBusMain",
  "Source": "orcabus.manual",
  "DetailType": "WorkflowRunUpdate",
  "Detail": {
    "status": "DRAFT",
    "timestamp": "2025-06-06T04:39:31Z",
    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd6789",
    "workflow": {
      "name": "dragen-wgts-dna",
      "version": "4.4.4",
    },
    "portalRunId": "20250606abcd6789",  // pragma: allowlist secret
    "linkedLibraries": [
      {
        "libraryId": "L2301197",
        "orcabusId": "lib.01JBMVHM2D5GCC7FTC20K4FDFK"
      }
    ]
  }
}
```

</details>

> [!NOTE]
> Please be aware of the following:

The DRAFT Event Populator uses default inputs to populate the non-file-like parameters. See the complete DRAFT [example](#complete-draft-event-example) below.

The defaults for the workflow version 4.4.4 are:

```json5
{
  // All '*Options' are optional but there are no defaults
  // So please ensure you set the options you need
  "alignmentOptions": {
    "enableDuplicateMarking": true
  },
  // targetedCallerOptions - Not required, options for the targeted caller
  "targetedCallerOptions": {
    "enableTargeted": [
      "cyp2d6"
    ]
  },
  // Snv Variant Caller Options
  // Not required, enableVariantCaller is always set to true
  "snvVariantCallerOptions": {
    "enableVcfCompression": true,
    // True by default
    "enableVcfIndexing": true,
    // True by default
    "qcDetectContamination": true,
    "vcMnvEmitComponentCalls": true,
    "vcCombinePhasedVariantsDistance": 2,
    "vcCombinePhasedVariantsDistanceSnvsOnly": 2
  }
}
```

> [!IMPORTANT]
> The DRAFT Event Populator does NOT perform a merge on any of your inputs and the default inputs.

This means if you specify the following in your data inputs payload:

```json5
// ...
{
  "data": {
    "inputs": {
      "alignmentOptions": {
        "enableDeterministicSort": true
      }
    }
  }
}
```

... then this provided `alignmentOptions` section will override the default and therefore "enableDuplicateMarking" will be omitted from the final DRAFT event.

#### Complete DRAFT event example

<details>

<summary>Click to expand</summary>

```json5
{
  "EventBusName": "OrcaBusMain",
  "Source": "orcabus.manual",
  "DetailType": "WorkflowRunUpdate",
  "Detail": {
    // status - Required - and must be set to DRAFT
    "status": "DRAFT",
    // timestamp - Required - set in UTC / ZULU time
    "timestamp": "2025-06-06T04:39:31Z",
    // workflow
    "workflow": {
      "orcabusId": "wfl.01K3F98TQJM8W3MQPKAKBPK26T",
      "name": "dragen-wgts-dna",
      "version": "4.4.4",
      "executionEnginePipelineId": "f6a4c255-5d49-4379-91ec-dd89b76a213f"
    },
    // workflowVersion - Required - Must be set to 4.4.4
    "workflowVersion": "4.4.4",
    // workflowRunName - Required - Nomenclature is umccr--automated--dragen-wgts-dna--<workflowVersion>--<portalRunId>
    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd6789",
    // portalRunId - Required - Must be set to a unique identifier for the run in the format YYYYMMDD<8-hex-digit-unique-id>
    "portalRunId": "20250606abcd6789",  // pragma: allowlist secret
    // pragma: allowlist secret
    // linkedLibraries - Required - List of linked libraries, in the format
    // 'libraryId': '<libraryId>', 'orcabusId': '<orcabusId>'
    "linkedLibraries": [
      {
        "libraryId": "L2301197",
        "orcabusId": "lib.01JBMVHM2D5GCC7FTC20K4FDFK"
      }
    ],
    // payload - The payload for the workflow run, containing all the necessary data
    "payload": {
      // version - The version of the payload schema used by this service
      // Not currently used by the service, but may be used in future
      "version": "2025.06.06",
      // data - The data for the workflow run, containing inputs, engine parameters, and tags
      "data": {
        // all inputs for the dragen-wgts-dna pipeline
        "inputs": {
          // All '*Options' are optional but there are no defaults
          // So please ensure you set the options you need
          "alignmentOptions": {
            "enableDuplicateMarking": true
          },
          // Not required, set to hg38 graph genome by default
          "reference": {
            "name": "hg38",
            "structure": "graph",
            "tarball": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-hash-tables/v11-r5/hg38-alt_masked-cnv-graph-hla-methyl_cg-rna/hg38-alt_masked.cnv.graph.hla.methyl_cg.rna-11-r5.0-1.tar.gz"
          },
          // somaticReference - Not required, set to hg38 linear by default
          "somaticReference": {
            "name": "hg38",
            "structure": "linear",
            "tarball": "s3://..."
          },
          // oraReference - Not required,
          // and only added in if any sequence data is in ORA format
          "oraReference": "s3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/reference-data/dragen-ora/v2/ora_reference_v2.tar.gz",
          // sampleName - Not required, the sample name for the workflow run
          // by default this is the libraryId
          "sampleName": "L2301197",
          // targetedCallerOptions - Not required, options for the targeted caller
          "targetedCallerOptions": {
            "enableTargeted": [
              "cyp2d6"
            ]
          },
          // sequenceData - The sequence data for the workflow run
          // Not required, will be populated based on the fastqListRowRgids under tags.fastqRgidList
          "sequenceData": {
            "fastqListRows": [
              {
                "rgid": "L2301197",
                "rglb": "L2301197",
                "rgsm": "L2301197",
                "lane": 1,
                "read1FileUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R1_001.fastq.ora",
                "read2FileUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/test_data/ora-testing/input_data/MDX230428_L2301197_S7_L004_R2_001.fastq.ora"
              }
            ]
          },
          // Snv Variant Caller Options
          // Not required, enableVariantCaller is always set to true
          "snvVariantCallerOptions": {
            "enableVcfCompression": true,
            // True by default
            "enableVcfIndexing": true,
            // True by default
            "qcDetectContamination": true,
            "vcMnvEmitComponentCalls": true,
            "vcCombinePhasedVariantsDistance": 2,
            "vcCombinePhasedVariantsDistanceSnvsOnly": 2
          }
        },
        // engineParameters - Parameters for the pipeline engine
        "engineParameters": {
          // Not required, defaults to the default pipeline for the workflowVersion specified
          "pipelineId": "f6a4c255-5d49-4379-91ec-dd89b76a213f",
          // Not required, defaults to the default project id
          "projectId": "ea19a3f5-ec7c-4940-a474-c31cd91dbad4",
          // Not required, defaults to the default workflow output prefix
          "outputUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/analysis/dragen-wgts-dna/20250606abcd6789/",
          // Not required, defaults to the default workflow logs prefix
          "logsUri": "s3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/logs/dragen-wgts-dna/20250606abcd6789/"
        },
        "tags": {
          // libraryId, required, the germline library ID for the workflow run
          "libraryId": "L2301197",
          // tumorLibraryId, only required for somatic workflows, the somatic library ID for the workflow run
          "tumorLibraryId": "L2301198",
          // fastqRgidList, not required, a list of fastq RGIDs for the workflow run
          // If not provided, will be populated from the fastq manager for the current fastq set for the library id provided
          "fastqRgidList": [
            "AAAAAAA+GGGGGGGG.4.240902_A01030_0366_ABCD1234567"
          ],
          // tumorFastqRgidList, only required for somatic workflows, a list of fastq RGIDs for the somatic workflow run
          "tumorFastqRgidList": [
            "CCCCCCC+TTTTTTTT.4.240902_A01030_0366_EFGH1234567"
          ],
          // subjectId, not required, the subject ID for the workflow run
          // If not provided, will be populated by the metadata manager from the libraryId provided
          "subjectId": "ExternalSubjectId",
          // individualId - not required, the individual ID for the workflow run
          "individualId": "InternalSubjectId",
        }
      }
    }
  }
}
```

</details>

#### Manually Validating Schemas,

We have generated JSON Schemas for the complete DRAFT WRU event **data** which you can find in the [`./app/event-schemas`](app/event-schemas) directory.

You can interactively check if your DRAFT or READY event data payload matches the schema using the following links:

- [Complete DRAFT WRU Event Data Schema Page](https://www.jsonschemavalidator.net/s/wSuvwypw)

#### Making your own DRAFT WRU events with BASH / JQ (new system)

There may be circumstances where you wish to generate DRAFT events manually, e.g. to explicitly trigger a workflow execution where automation failed or is not available. The below is a quick solution for generating a DRAFT WRU event for a somatic WGTS DNA workflow. Omit setting the `TUMOR_LIBRARY_ID` variable for running a germline only workflow.

> [!NOTE]
> This is a minimal example. It assumes that the rest of the required information can be retrieved and filled by the DRAFT Event Populator.

The DRAFT Event Populator will also pull necessary fastq files out of archive.

For details, see [PM.DWD.1 - Manual Pipeline Execution](./docs/operation/SOP/PM.DWD.1/PM.DWD.1-ManualPipelineExecution.md)

#### Making your own DRAFT WRSC events with BASH / JQ (legacy system)

There may be circumstances where you wish to generate DRAFT WRSC events manually, the below is a quick solution for
generating a DRAFT for a somatic WGTS DNA workflow. Omit setting the TUMOR_LIBRARY_ID variable for running a germline
only workflow.

The DRAFT populator step function will also pull necessary fastq files out of archive.

For a detailed procedure, see [Manual Pipeline Execution (legacy)](./docs/operation/examples/WRSC-DRAFT/ManualPipelineExecution.md)

#### Release management

The service employs a fully automated CI/CD pipeline that automatically builds and releases all changes to the `main`
code branch.

A developer must enable the CodePipeline transition manually through the UI to promote changes to the `production`
environment.


Infrastructure & Deployment
--------------------------------------------------------------------------------

Short description with diagrams where appropriate.
Deployment settings / configuration (e.g. CodePipeline(s) / automated builds).

Infrastructure and deployment are managed via CDK. This template provides two types of CDK entry points: `cdk-stateless`
and `cdk-stateful`.

### Stateful Stack

The stateful stack for this service includes the following resources:

**Schemas**

* We upload the complete WRU schema to the AWS Schemas registry,
  this is used to validate a DRAFT event before it is allowed to mature into a READY event

We currently maintain following schemas:

* dragen-wgts-dna-complete-data-draft-schema.json

**SSM Parameters List**

These parameters are used to help generate READY Events for the Dragen WGTS DNA pipeline from DRAFT events.

All SSM parameters are under the prefix `/orcabus/workflows/dragen-wgts-dna/`

* workflowName: The name of the workflow managed by this service (dragen-wgts-dna)
* workflowVersion: The workflow version 4.4.4
* inputsByWorkflowVersion: Mapping default input chunks to workflow versions, one ssm parameter per workflow version
* payloadVersion: The version of the payload schema used by this service (NA)
* engine parameters
    * pipelineIdsByWorkflowVersion: ICAv2 pipeline IDs by workflow version, one ssm parameter per workflow version
    * icav2ProjectId: The default ICAv2 project ID for this service (development for dev, production for prod)
    * logsPrefix: The default prefix for logs generated by this service
    * outputPrefix: The default prefix for outputs generated by this service
* reference parameters:
    * default reference path by workflow version, one ssm parameter per workflow version
    * default somatic reference path by workflow version, one ssm parameter per workflow version
    * default ora reference version path

We also map the schemas in this stack to SSM parameters.

### Stateless Stack

The stateless stack for this service includes the following resources:

#### Step Functions

**Dragen WGTS DNA DRAFT to Completed DRAFT State Machine**

From the dragen WGTS DNA DRAFT event, we populate all inputs to make another DRAFT event, complete with all required
inputs.

![draft-to-completed-draft-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-complete-draft-schema.svg)

**Dragen WGTS DNA Validate DRAFT and Put READY Event**

Take in a dragen WGTS DNA DRAFT event, make sure it's valid, and then generate a READY event for the dragen WGTS DNA
pipeline.

![validate-draft-and-put-ready-event-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-validate-draft-and-put-ready-event.svg)

**Dragen WGTS DNA READY to ICAv2 WES Submitted State Machine**

Takes in a READY event for the dragen WGTS DNA pipeline, and generates a ICAv2 WES workflow request.

![ready-to-icav2-wes-submitted-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-ready-to-icav2-wes-submitted.svg)

**ICAv2 WES Event to WRSC Event**

From the ICAv2 WES Analysis State Change event, we parse the analysis state and workflow name to generate a WRSC event.

![icav2-wes-event-to-wrsc-event-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-handle-icav2-analysis-state-change.svg)

### CDK Commands

You can access CDK commands using the `pnpm` wrapper script.

- **`cdk-stateless`**: Used to deploy stacks containing stateless resources (e.g., AWS Lambda), which can be easily
  redeployed without side effects.
- **`cdk-stateful`**: Used to deploy stacks containing stateful resources (e.g., AWS DynamoDB, AWS RDS), where
  redeployment may not be ideal due to potential side effects.

The type of stack to deploy is determined by the context set in the `./bin/deploy.ts` file. This ensures the correct
stack is executed based on the provided context.

For example:

```sh
# Deploy a stateless stack
pnpm cdk-stateless <command>

# Deploy a stateful stack
pnpm cdk-stateful <command>
```

### Stacks

This CDK project manages multiple stacks. The root stack (the only one that does not include `DeploymentPipeline` in its
stack ID) is deployed in the toolchain account and sets up a CodePipeline for cross-environment deployments to `beta`,
`gamma`, and `prod`.

#### Stateful Stack

To list all available stateful stacks, run:

```sh
pnpm cdk-stateful ls
```

Output:

```shell
StatefulDragenWgtsDnaPipeline
StatefulDragenWgtsDnaPipeline/StatefulDragenWgtsDnaPipeline/OrcaBusBeta/StatefulDragenWgtsDnaPipeline (OrcaBusBeta-StatefulDragenWgtsDnaPipeline)
StatefulDragenWgtsDnaPipeline/StatefulDragenWgtsDnaPipeline/OrcaBusGamma/StatefulDragenWgtsDnaPipeline (OrcaBusGamma-StatefulDragenWgtsDnaPipeline)
StatefulDragenWgtsDnaPipeline/StatefulDragenWgtsDnaPipeline/OrcaBusProd/StatefulDragenWgtsDnaPipeline (OrcaBusProd-StatefulDragenWgtsDnaPipeline)
```

#### Stateless Stack

To list all available stateless stacks, run:

```sh
pnpm cdk-stateless ls
```

Output:

```sh
StatelessDragenWgtsDnaPipelineManager
StatelessDragenWgtsDnaPipelineManager/StatelessDragenWgtsDnaPipeline/OrcaBusBeta/StatelessDragenWgtsDnaPipelineManager (OrcaBusBeta-StatelessDragenWgtsDnaPipelineManager)
StatelessDragenWgtsDnaPipelineManager/StatelessDragenWgtsDnaPipeline/OrcaBusGamma/StatelessDragenWgtsDnaPipelineManager (OrcaBusGamma-StatelessDragenWgtsDnaPipelineManager)
StatelessDragenWgtsDnaPipelineManager/StatelessDragenWgtsDnaPipeline/OrcaBusProd/StatelessDragenWgtsDnaPipelineManager (OrcaBusProd-StatelessDragenWgtsDnaPipelineManager)
```

Development
--------------------------------------------------------------------------------

### Project Structure :construct:

The root of the project is an AWS CDK project where the main application logic lives inside the `./app` folder.

The project is organized into the following key directories:

- **`./app`**: Contains the main application logic. This includes the lambda scripts, the event schemas and the step
  functions in template ASL format.

- **`./bin/deploy.ts`**: Serves as the entry point of the application. It initializes two root stacks: `stateless` and
  `stateful`. You can remove one of these if your service does not require it.

- **`./infrastructure`**: Contains the infrastructure code for the project:
    - **`./infrastructure/toolchain`**: Includes stacks for the stateless and stateful resources deployed in the
      toolchain account. These stacks primarily set up the CodePipeline for cross-environment deployments.
    - **`./infrastructure/stage`**: Defines the stage stacks for different environments:
        - **`./infrastructure/stage/config.ts`**: Contains environment-specific configuration files (e.g., `beta`,
          `gamma`, `prod`).
        - **`./infrastructure/stage/constants.ts`**: Application specific constants used across the stack
        - **`./infrastructure/stage/statefulApplicationStack.ts`**: The CDK stack entry point for provisioning stateful
          resources required by the application in `./app`.
        - **`./infrastructure/stage/statelessApplicationStack.ts`**: The CDK stack entry point for provisioning
          stateless resources required by the application in `./app`.
        - **`./infrastructure/stage/<service>`**: Interfaces and functions built per service, this might be lambda
          function builder constructs, or dynamodb table builder constructs specific to the application

- **`.github/workflows/pr-tests.yml`**: Configures GitHub Actions to run tests for `make check` (linting and code
  style), tests defined in `./test`, and `make test` for the `./app` directory. Modify this file as needed to ensure the
  tests are properly configured for your environment.

- **`./test`**: Contains tests for CDK code compliance against `cdk-nag`. You should modify these test files to match
  the resources defined in the `./infrastructure` folder.

### Setup

#### Requirements

```sh
node --version
v22.9.0

# Update Corepack (if necessary, as per pnpm documentation)
npm install --global corepack@latest

# Enable Corepack to use pnpm
corepack enable pnpm

```

#### Install Dependencies

To install all required dependencies, run:

```sh
make install
```

#### Update Dependencies

To update dependencies, run:

```sh
pnpm update
```

### Conventions

### Linting & Formatting

Automated checks are enforces via pre-commit hooks, ensuring only checked code is committed. For details consult the
`.pre-commit-config.yaml` file.

Manual, on-demand checking is also available via `make` targets (see below). For details consult the `Makefile` in the
root of the project.

To run linting and formatting checks on the root project, use:

```sh
make check
```

To automatically fix issues with ESLint and Prettier, run:

```sh
make fix
```

### Testing

Unit tests are available for most of the business logic. Test code is hosted alongside business in `/tests/`
directories.

```sh
make test
```

Glossary & References
--------------------------------------------------------------------------------

| Term | Description |
|------|-------------|
| AWS CLI | The Command Line Interface (CLI) provided by AWS. (https://aws.amazon.com/cli/) |
| JQ | A JSON command line processor facilitating the work with JSON data. (https://jqlang.org/) |

For general terms and expressions used across OrcaBus services, please see the
platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).
