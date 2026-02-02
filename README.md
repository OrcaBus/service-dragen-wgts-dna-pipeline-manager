# Dragen WGTS DNA Pipeline Manager
================================================================================

- [Description](#description)
  - [Summary](#summary)
  - [Ready Event Creation](#ready-event-creation)
  - [Consumed Events](#consumed-events)
  - [Published Events](#published-events)
  - [Draft Event](#draft-event)
    - [Draft Event Submission](#draft-event-submission)
    - [Draft Data Schema Validation](#draft-data-schema-validation)
  - [Release management](#release-management)
  - [Related Services](#related-services)
    - [Upstream Pipelines](#upstream-pipelines)
    - [Downstream Pipelines](#downstream-pipelines)
    - [Primary Services](#primary-services)
- [Infrastructure \& Deployment](#infrastructure--deployment)
  - [Stateful Stack](#stateful-stack)
  - [Stateless Stack](#stateless-stack)
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

## Description
--------------------------------------------------------------------------------

### Summary

This is the Dragen WGTS DNA Pipeline Management service, responsible for managing the Dragen WGTS DNA pipeline.

The [Dragen WGTS DNA Pipeline](https://help.dragen.illumina.com/product-guide/dragen-v4.4/dragen-dna-pipeline) is used
for alignment, variant calling of whole genome sequencing data for both germline and somatic data.

The pipeline itself runs on ICAv2 through CWL,
see [our CWL releases page](https://github.com/umccr/cwl-ica/releases?q=dragen-wgts-dna&expanded=true)
that allows us to run both the somatic and germline steps simultaneously in a single workflow run.

The orchestration logic is per the
standard [ICAv2-centric Pipeline Architecture](https://github.com/OrcaBus/wiki/blob/main/orcabus/platform/pipelines.md#pipeline-orchestration-general-logic)

### Ready Event Creation

![events-overview](docs/drawio-exports/draft-to-ready.drawio.svg)

### Consumed Events

| Name / DetailType             | Source                    | Schema Link                                                                                                                                | Description                                                      |
|-------------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| `WorkflowRunStateChange`      | `orcabus.workflowmanager` | [WorkflowRunStateChange](https://github.com/OrcaBus/wiki/tree/main/orcabus-platform#workflowrunstatechange)                                | Source of updates on WorkflowRuns (expected pipeline executions) |
| `Icav2WesAnalysisStateChange` | `orcabus.icav2wes`        | [Icav2WesAnalysisStateChange](https://github.com/OrcaBus/service-icav2-wes-manager/blob/main/app/event-schemas/analysis-state-change.json) | ICAv2 WES Analysis State Change event                            |

### Published Events

| Name / DetailType   | Source                  | Schema Link                                                                                                 | Description                                 |
|---------------------|-------------------------|-------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| `WorkflowRunUpdate` | `orcabus.dragenwgtsdna` | [WorkflowRunUpdate](https://github.com/OrcaBus/wiki/blob/main/orcabus/platform/events.md#workflowrunupdate) | Reporting any updates to the pipeline state |

### Draft Event

A workflow run must be placed into a DRAFT state before it can be started.

This is to ensure that only valid workflow runs are started, and that all required data is present.

This service is responsible for both populating and validating draft workflow runs.

A draft event may even be submitted without a payload.

#### Draft Event Submission

To submit a Dragen WGTS DNA draft event, please follow the [PM.DWD.1 SOP](/docs/operation/SOP/README.md#PM.DWD.1) in our
SOPs documentation.

#### Draft Data Schema Validation

We have generated JSON schemas for the complete DRAFT WRU event **data** which you can find in the
[`app/event-schemas` directory](/app/event-schemas).

You can interactively check if your DRAFT event data payload matches the schema using the following links:

- [Complete DRAFT WRU Event Data Schema Page](https://www.jsonschemavalidator.net/s/JX96lXfY)

### Release management

The service employs a fully automated CI/CD pipeline that automatically builds and releases all changes to the `main`
code branch.

A developer must enable the CodePipeline transition manually through the UI to promote changes to the `production`
environment.

### Related Services

#### Upstream Pipelines

- [Analysis Glue](https://github.com/OrcaBus/service-analysis-glue)

#### Downstream Pipelines

- [Oncoanalyser WGTS DNA](https://github.com/OrcaBus/service-oncoanalyser-wgts-dna-pipeline-manager)
- [Oncoanalyser WGTS DNA/RNA](https://github.com/OrcaBus/service-oncoanalyser-wgts-both-pipeline-manager)

#### Primary Services

- [ICAv2 WES Manager](https://github.com/OrcaBus/service-icav2-wes-manager)
- [Workflow Manager](https://github.com/OrcaBus/service-workflow-manager)
- [Fastq Glue](https://github.com/OrcaBus/service-fastq-glue)


Infrastructure & Deployment
--------------------------------------------------------------------------------

> Deployment settings / configuration (e.g. CodePipeline(s) / automated builds).

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

#### Linting & Formatting

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

For general terms and expressions used across OrcaBus services, please see the
platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).
