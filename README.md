Dragen WGTS DNA Pipeline Manager
================================================================================

<!-- TOC -->
* [Dragen WGTS DNA Pipeline Manager](#dragen-wgts-dna-pipeline-manager)
  * [Description](#description)
    * [Summary](#summary)
    * [Events Overview](#events-overview)
    * [Consumed Events](#consumed-events)
    * [Published Events](#published-events)
      * [Release management](#release-management)
  * [Infrastructure & Deployment](#infrastructure--deployment)
    * [Stateful Stack](#stateful-stack)
    * [Stateless Stack](#stateless-stack)
      * [Step Functions](#step-functions)
    * [CDK Commands :construction:](#cdk-commands-construction)
    * [Stacks](#stacks)
  * [Development](#development)
    * [Project Structure :construct:](#project-structure-construct)
    * [Setup :construction:](#setup-construction)
      * [Requirements](#requirements)
      * [Install Dependencies :construction:](#install-dependencies-construction)
    * [Conventions](#conventions)
    * [Linting & Formatting](#linting--formatting)
    * [Testing](#testing)
  * [Glossary & References](#glossary--references)
<!-- TOC -->


Description
--------------------------------------------------------------------------------

### Summary

This is the Dragen WGTS DNA Pipeline Management service,
responsible for managing the Dragen WGTS DNA pipeline.

The pipeline itself runs on ICAv2 through CWL :construction:

### Events Overview

We listen to READY WRSC events where the the workflow name is equal to `dragen-wgts-dna-pipeline`.

We parse this to the ICAv2 WES Service to generate a ICAv2 WES workflow request.

We then parse ICAv2 Analysis State Change events to update the state of the workflow in our service.

![events-overview](docs/drawio-exports/dragen-tso-ctdna.drawio.svg)

### Consumed Events

| Name / DetailType        | Source        | Schema Link       | Description       |
|--------------------------|---------------|-------------------|-------------------|
| `WorkflowRunStateChange` | `orcabus.any` | <schema link> | READY statechange |
 | `Icav2WesAnalysisStateChange` | `orcabus.icav2wes` | <schema link> | ICAv2 WES Analysis State Change event |

### Published Events

| Name / DetailType | Source                  | Schema Link       | Description           |
|-------------------|-------------------------|-------------------|-----------------------|
| `WorkflowRunStateChange` | `orcabus.dragenwgtsdna` | <schema link> | Analysis state change |


### Draft Event Example

<details>

<summary>Click to expand</summary>

```json5
{
  "EventBusName": "OrcaBusMain",
  "Source": "orcabus.manual",
  "DetailType": "WorkflowRunStateChange",
  "Detail": {
    // status - Required - and must be set to DRAFT
    "status": "DRAFT",
    // timestamp - Required - set in UTC / ZULU time
    "timestamp": "2025-06-06T04:39:31Z",
    // workflowName - Required - Must be set to dragen-wgts-dna
    "workflowName": "dragen-wgts-dna",
    // workflowVersion - Required - Must be set to 4.4.4
    "workflowVersion": "4.4.4",
    // workflowRunName - Required - Nomenclature is umccr--automated--dragen-wgts-dna--<workflowVersion>--<portalRunId>
    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd6789",
    // portalRunId - Required - Must be set to a unique identifier for the run in the format YYYYMMDD<8-hex-digit-unique-id>
    "portalRunId": "20250606abcd6789",  // pragma: allowlist secret
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
            "enableVcfCompression": true,  // True by default
            "enableVcfIndexing": true,  // True by default
            "qcDetectContamination": true,
            "vcMnvEmitComponentCalls": true,
            "vcCombinePhasedVariantsDistance": 2,
            "vcCombinePhasedVariantsDistanceSnvsOnly": 2
          }
        },
        // engineParameters - Parameters for the pipeline engine
        "engineParameters": {
          // Not required, defaults to the default pipeline for the workflowVersion specified
          "pipelineId": "5009335a-8425-48a8-83c4-17c54607b44a",
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

Draft minimal example

<details>

<summary>Click to expand</summary>

```json5
{
  "EventBusName": "OrcaBusMain",
  "Source": "orcabus.manual",
  "DetailType": "WorkflowRunStateChange",
  "Detail": {
    "status": "DRAFT",
    "timestamp": "2025-06-06T04:39:31Z",
    "workflowName": "dragen-wgts-dna",
    "workflowVersion": "4.4.4",
    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd6789",
    "portalRunId": "20250606abcd6789",  // pragma: allowlist secret
    "linkedLibraries": [
      {
        "libraryId": "L2301197",
        "orcabusId": "lib.01JBMVHM2D5GCC7FTC20K4FDFK"
      }
    ],
    "payload": {
      "version": "2025.06.06",
      "data": {
        "inputs": {
          "alignmentOptions": {
            "enableDuplicateMarking": true
          },
          "targetedCallerOptions": {
            "enableTargeted": [
              "cyp2d6"
            ]
          },
          "snvVariantCallerOptions": {
            "qcDetectContamination": true,
            "vcMnvEmitComponentCalls": true,
            "vcCombinePhasedVariantsDistance": 2,
            "vcCombinePhasedVariantsDistanceSnvsOnly": 2
          }
        },
        "tags": {
          "libraryId": "L2301197",
          "tumorLibraryId": "L2301198"
        }
      }
    }
  }
}
```

</details>


### Ready Event example

<details>

<summary>Click to expand</summary>

```json5
{
  "EventBusName": "OrcaBusMain",
  "Source": "orcabus.manual",
  "DetailType": "WorkflowRunStateChange",
  "Detail": {
    // status - Required - and must be set to READY
    "status": "READY",
    // timestamp - Required - set in UTC / ZULU time
    "timestamp": "2025-06-06T04:39:31Z",
    // workflowName - Required - Must be set to dragen-wgts-dna
    "workflowName": "dragen-wgts-dna",
    // workflowVersion - Required - Must be set to 4.4.4
    "workflowVersion": "4.4.4",
    // workflowRunName - Required - Nomenclature is umccr--automated--dragen-wgts-dna--<workflowVersion>--<portalRunId>
    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd6789",
    // portalRunId - Required - Must be set to a unique identifier for the run in the format YYYYMMDD<8-hex-digit-unique-id>
    "portalRunId": "20250606abcd6789",  // pragma: allowlist secret
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
            "enableVcfCompression": true,  // True by default
            "enableVcfIndexing": true,  // True by default
            "qcDetectContamination": true,
            "vcMnvEmitComponentCalls": true,
            "vcCombinePhasedVariantsDistance": 2,
            "vcCombinePhasedVariantsDistanceSnvsOnly": 2
          }
        },
        // engineParameters - Parameters for the pipeline engine
        "engineParameters": {
          // Not required, defaults to the default pipeline for the workflowVersion specified
          "pipelineId": "5009335a-8425-48a8-83c4-17c54607b44a",
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

We have generated JSON Schemas for both the draft and ready events. You can find them in the [`./app/event-schemas`](app/event-schemas) directory.

You can interactively check if your DRAFT or READY event matches the schema using the following links:

- [Draft Event Schema Page](https://www.jsonschemavalidator.net/s/auxIl15h)
- [Ready Event Schema Page](https://www.jsonschemavalidator.net/s/74jG3Bru)

#### Release management

The service employs a fully automated CI/CD pipeline that automatically builds and releases all changes to the `main` code branch.

A developer must enable the CodePipeline transition manually through the UI to promote changes to the `production` environment.


Infrastructure & Deployment
--------------------------------------------------------------------------------

Short description with diagrams where appropriate.
Deployment settings / configuration (e.g. CodePipeline(s) / automated builds).

Infrastructure and deployment are managed via CDK. This template provides two types of CDK entry points: `cdk-stateless` and `cdk-stateful`.


### Stateful Stack

The stateful stack for this service includes the following resources:

These parameters are used to help generate READY Events for the Dragen WGTS DNA pipeline from DRAFT events.

**SSM Parameters List**

* workflowName: The name of the workflow managed by this service (dragen-wgts-dna)
* workflowVersion: The workflow version 4.4.4
* prefixPipelineIdsByWorkflowVersion: SSM Parameter root path mapping workflow versions to default ICAv2 pipeline IDs
* icav2ProjectId: The default ICAv2 project ID for this service (development for dev, production for prod)
* payloadVersion: The version of the payload schema used by this service (NA)
* logsPrefix: The default prefix for logs generated by this service
* outputPrefix: The default prefix for outputs generated by this service

### Stateless Stack

The stateless stack for this service includes the following resources:

#### Step Functions

**Dragen WGTS DNA Draft to Ready State Machine**

From the dragen WGTS DNA DRAFT event, we parse the event to generate a READY event for the Dragen WGTS DNA pipeline.

![draft-to-ready-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-draft-to-ready.svg)

**Dragen WGTS DNA Ready To ICAv2 WES Submitted**

From the dragen WGTS DNA READY event, we parse the workflow name and version to generate a ICAv2 WES workflow request.

![ready-to-icav2-wes-submitted-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-ready-to-icav2-wes-submitted.svg)

**ICAv2 WES Event to WRSC Event**

From the ICAv2 WES Analysis State Change event, we parse the analysis state and workflow name to generate a WRSC event.

![icav2-wes-event-to-wrsc-event-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-handle-icav2-analysis-state-change.svg)


### CDK Commands :construction:

You can access CDK commands using the `pnpm` wrapper script.

- **`cdk-stateless`**: Used to deploy stacks containing stateless resources (e.g., AWS Lambda), which can be easily redeployed without side effects.
- **`cdk-stateful`**: Used to deploy stacks containing stateful resources (e.g., AWS DynamoDB, AWS RDS), where redeployment may not be ideal due to potential side effects.

The type of stack to deploy is determined by the context set in the `./bin/deploy.ts` file. This ensures the correct stack is executed based on the provided context.

For example:

```sh
# Deploy a stateless stack
pnpm cdk-stateless <command>

# Deploy a stateful stack
pnpm cdk-stateful <command>
```

### Stacks

This CDK project manages multiple stacks. The root stack (the only one that does not include `DeploymentPipeline` in its stack ID) is deployed in the toolchain account and sets up a CodePipeline for cross-environment deployments to `beta`, `gamma`, and `prod`.

To list all available stacks, run:

```sh
pnpm cdk-stateless ls
```

Example output:

```sh
OrcaBusStatelessServiceStack
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusBeta/DeployStack (OrcaBusBeta-DeployStack)
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusGamma/DeployStack (OrcaBusGamma-DeployStack)
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusProd/DeployStack (OrcaBusProd-DeployStack)
```


Development
--------------------------------------------------------------------------------

### Project Structure :construct:

The root of the project is an AWS CDK project where the main application logic lives inside the `./app` folder.

The project is organized into the following key directories:

- **`./app`**: Contains the main application logic. You can open the code editor directly in this folder, and the application should run independently.

- **`./bin/deploy.ts`**: Serves as the entry point of the application. It initializes two root stacks: `stateless` and `stateful`. You can remove one of these if your service does not require it.

- **`./infrastructure`**: Contains the infrastructure code for the project:
  - **`./infrastructure/toolchain`**: Includes stacks for the stateless and stateful resources deployed in the toolchain account. These stacks primarily set up the CodePipeline for cross-environment deployments.
  - **`./infrastructure/stage`**: Defines the stage stacks for different environments:
    - **`./infrastructure/stage/config.ts`**: Contains environment-specific configuration files (e.g., `beta`, `gamma`, `prod`).
    - **`./infrastructure/stage/stack.ts`**: The CDK stack entry point for provisioning resources required by the application in `./app`.

- **`.github/workflows/pr-tests.yml`**: Configures GitHub Actions to run tests for `make check` (linting and code style), tests defined in `./test`, and `make test` for the `./app` directory. Modify this file as needed to ensure the tests are properly configured for your environment.

- **`./test`**: Contains tests for CDK code compliance against `cdk-nag`. You should modify these test files to match the resources defined in the `./infrastructure` folder.


### Setup :construction:

#### Requirements

```sh
node --version
v22.9.0

# Update Corepack (if necessary, as per pnpm documentation)
npm install --global corepack@latest

# Enable Corepack to use pnpm
corepack enable pnpm

```

#### Install Dependencies :construction:

To install all required dependencies, run:

```sh
make install
```

### Conventions

### Linting & Formatting

Automated checks are enforces via pre-commit hooks, ensuring only checked code is committed. For details consult the `.pre-commit-config.yaml` file.

Manual, on-demand checking is also available via `make` targets (see below). For details consult the `Makefile` in the root of the project.


To run linting and formatting checks on the root project, use:

```sh
make check
```

To automatically fix issues with ESLint and Prettier, run:

```sh
make fix
```

### Testing


Unit tests are available for most of the business logic. Test code is hosted alongside business in `/tests/` directories.

```sh
make test
```

Glossary & References
--------------------------------------------------------------------------------

For general terms and expressions used across OrcaBus services, please see the platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).

Service specific terms:

| Term      | Description                                      |
|-----------|--------------------------------------------------|
| Foo | ... |
| Bar | ... |
