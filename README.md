Dragen WGTS DNA Pipeline Manager
================================================================================

- [Description](#description)
    - [Summary](#summary)
    - [Events Overview](#events-overview)
    - [Consumed Events](#consumed-events)
    - [Published Events](#published-events)
    - [Draft Event Example](#draft-event-example)
    - [Ready Event example](#ready-event-example)
        - [Manually Validating Schemas,](#manually-validating-schemas)
        - [Making your own draft events with BASH / JQ](#making-your-own-draft-events-with-bash--jq)
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
    - [Setup :construction:](#setup-construction)
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

The pipeline itself runs on ICAv2 through CWL

### Events Overview

**Draft Population**
We listen to DRAFT WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We then try to populate the inputs for the workflow run, and generate a complete DRAFT event.

**Draft Validation**
We listen to DRAFT WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We then validate the DRAFT event against the schema, and if valid, we generate a READY event.

**Ready Event**
We listen to READY WRSC events where the workflow name is equal to `dragen-wgts-dna`.
We parse this to the ICAv2 WES Service to generate a ICAv2 WES workflow request.

**ICAv2 WES Analysis State Change**
We then parse ICAv2 Analysis State Change events to update the state of the workflow in our service.

![events-overview](docs/drawio-exports/dragen-wgts-dna.drawio.svg)

### Consumed Events

| Name / DetailType             | Source             | Schema Link   | Description                           |
|-------------------------------|--------------------|---------------|---------------------------------------|
| `WorkflowRunStateChange`      | `orcabus.any`      | <schema link> | READY statechange                     |
| `Icav2WesAnalysisStateChange` | `orcabus.icav2wes` | <schema link> | ICAv2 WES Analysis State Change event |

### Published Events

| Name / DetailType        | Source                  | Schema Link   | Description           |
|--------------------------|-------------------------|---------------|-----------------------|
| `WorkflowRunStateChange` | `orcabus.dragenwgtsdna` | <schema link> | Analysis state change |

### Draft Event Example

Draft minimal example

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

Please be aware of the following:

We use a default inputs json to populate the non-file-like parameters, the default for the workflow version 4.4.4 is so:

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

**THE DRAFTS POPULATOR SFN DOES NOT PERFORM A RECURSIVE MERGE ON BETWEEN ANY OF YOUR INPUTS AND THE DEFAULT INPUTS**

This means if you specify the following in your data inputs payload

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

"enableDuplicateMarking" will be omitted from the final draft event.

### Complete Draft Event example

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

We have generated JSON Schemas for the complete draft event data which you can find in the [
`./app/event-schemas`](app/event-schemas) directory.

You can interactively check if your DRAFT or READY event data payload matches the schema using the following links:

- [Complete Draft Data Event Schema Page](https://www.jsonschemavalidator.net/s/wSuvwypw)

#### Making your own draft events with BASH / JQ (dev)

There may be circumstances where you wish to generate WRSC events manually, the below is a quick solution for
generating a draft for a somatic wgts dna workflow. Omit setting the TUMOR_LIBRARY_ID variable for running a germline
only workflow.

The draft populator step function will also pull necessary fastq files out of archive.

<details>

<summary>Click to expand</summary>

```shell
# Globals
EVENT_BUS_NAME="OrcaBusMain"
DETAIL_TYPE="WorkflowRunUpdate"
SOURCE="orcabus.manual"

WORKFLOW_NAME="dragen-wgts-dna"
WORKFLOW_VERSION="4.4.4"
EXECUTION_ENGINE="ICA"
CODE_VERSION="dd0e8c"

PAYLOAD_VERSION="2025.06.24"

# Glocals
LIBRARY_ID="L2300950"
TUMOR_LIBRARY_ID="L2300943"

# Functions
get_hostname_from_ssm(){
  aws ssm get-parameter \
    --name "/hosted_zone/umccr/name" \
    --output json | \
  jq --raw-output \
    '.Parameter.Value'
}

get_orcabus_token(){
  aws secretsmanager get-secret-value \
    --secret-id orcabus/token-service-jwt \
    --output json \
    --query SecretString | \
  jq --raw-output \
    'fromjson | .id_token'
}

get_pipeline_id_from_workflow_version(){
  local workflow_version="$1"
  aws ssm get-parameter \
    --name "/orcabus/workflows/dragen-wgts-dna/pipeline-ids-by-workflow-version/${workflow_version}" \
    --output json | \
  jq --raw-output \
    '.Parameter.Value'
}

get_library_obj_from_library_id(){
  local library_id="$1"
  curl --silent --fail --show-error --location \
    --header "Authorization: Bearer $(get_orcabus_token)" \
    --url "https://metadata.$(get_hostname_from_ssm)/api/v1/library?libraryId=${library_id}" | \
  jq --raw-output \
    '
      .results[0] |
      {
        "libraryId": .libraryId,
        "orcabusId": .orcabusId
      }
    '
}

generate_portal_run_id(){
  echo "$(date -u +'%Y%m%d')$(openssl rand -hex 4)"
}

get_linked_libraries(){
  local library_id="$1"
  local tumor_library_id="${2-}"

  linked_library_obj=$(get_library_obj_from_library_id "$library_id")

  if [ -n "$tumor_library_id" ]; then
    tumor_linked_library_obj=$(get_library_obj_from_library_id "$tumor_library_id")
  else
    tumor_linked_library_obj="{}"
  fi

  jq --null-input --compact-output --raw-output \
    --argjson libraryObj "$linked_library_obj" \
    --argjson tumorLibraryObj "$tumor_linked_library_obj" \
    '
      [
          $libraryObj,
          $tumorLibraryObj
      ] |
      # Filter out empty values, tumorLibraryId is optional
      # Then write back to JSON
      map(select(length > 0))
    '
}

get_workflow(){
  local workflow_name="$1"
  local workflow_version="$2"
  local execution_engine="$3"
  local execution_engine_pipeline_id="$4"
  local code_version="$5"
  curl --silent --fail --show-error --location \
    --request GET \
    --get \
    --header "Authorization: Bearer $(get_orcabus_token)" \
    --url "https://workflow.$(get_hostname_from_ssm)/api/v1/workflow" \
    --data "$( \
      jq \
       --null-input --compact-output --raw-output \
       --arg workflowName "$workflow_name" \
       --arg workflowVersion "$workflow_version" \
       --arg executionEngine "$execution_engine" \
       --arg executionEnginePipelineId "$execution_engine_pipeline_id" \
       --arg codeVersion "$code_version" \
       '
         {
            "name": $workflowName,
            "version": $workflowVersion,
            "executionEngine": $executionEngine,
            "executionEnginePipelineId": $executionEnginePipelineId,
            "codeVersion": $codeVersion
         } |
         to_entries |
         map(
           "\(.key)=\(.value)"
         ) |
         join("&")
       ' \
    )" | \
  jq --compact-output --raw-output \
    '
      .results[0]
    '
}

# Generate the event
event_cli_json="$( \
  jq --null-input --raw-output \
    --arg eventBusName "$EVENT_BUS_NAME" \
    --arg detailType "$DETAIL_TYPE" \
    --arg source "$SOURCE" \
    --argjson workflow "$(get_workflow \
      "${WORKFLOW_NAME}" "${WORKFLOW_VERSION}" \
      "${EXECUTION_ENGINE}" "$(get_pipeline_id_from_workflow_version "${WORKFLOW_VERSION}")" \
      "${CODE_VERSION}"
    )" \
    --arg payloadVersion "$PAYLOAD_VERSION" \
    --arg portalRunId "$(generate_portal_run_id)" \
    --argjson libraries "$(get_linked_libraries "${LIBRARY_ID}" "${TUMOR_LIBRARY_ID}")" \
    '
      {
        # Standard fields for the event
        "EventBusName": $eventBusName,
        "DetailType": $detailType,
        "Source": $source,
        # Detail must be a JSON object in string format
        "Detail": (
          {
            "status": "DRAFT",
            "timestamp": (now | todateiso8601),
            "workflow": $workflow,
            "workflowRunName": ("umccr--automated--" + $workflow["name"] + "--" + ($workflow["version"] | gsub("\\."; "-")) + "--" + $portalRunId),
            "portalRunId": $portalRunId,
            "libraries": $libraries,
          } |
          tojson
        )
      } |
      # Now wrap into an "entry" for the CLI
      {
        "Entries": [
          .
        ]
      }
    ' \
)"

aws events put-events --no-cli-pager --cli-input-json "${event_cli_json}"
```

</details>

#### Making your own draft events with BASH / JQ (prod)

There may be circumstances where you wish to generate WRSC events manually, the below is a quick solution for
generating a draft for a somatic wgts dna workflow. Omit setting the TUMOR_LIBRARY_ID variable for running a germline
only workflow.

The draft populator step function will also pull necessary fastq files out of archive.

<details>

<summary>Click to expand</summary>

```shell
# Globals
EVENT_BUS_NAME="OrcaBusMain"
DETAIL_TYPE="WorkflowRunStateChange"
SOURCE="orcabus.manual"

WORKFLOW_NAME="dragen-wgts-dna"
WORKFLOW_VERSION="4.4.4"

PAYLOAD_VERSION="2025.06.24"

# Glocals
LIBRARY_ID="L2300950"
TUMOR_LIBRARY_ID="L2300943"

# Functions
get_hostname_from_ssm(){
  aws ssm get-parameter \
    --name "/hosted_zone/umccr/name" \
    --output json | \
  jq --raw-output \
    '.Parameter.Value'
}

get_orcabus_token(){
  aws secretsmanager get-secret-value \
    --secret-id orcabus/token-service-jwt \
    --output json \
    --query SecretString | \
  jq --raw-output \
    'fromjson | .id_token'
}

get_pipeline_id_from_workflow_version(){
  local workflow_version="$1"
  aws ssm get-parameter \
    --name "/orcabus/workflows/dragen-wgts-dna/pipeline-ids-by-workflow-version/${workflow_version}" \
    --output json | \
  jq --raw-output \
    '.Parameter.Value'
}

get_library_obj_from_library_id(){
  local library_id="$1"
  curl --silent --fail --show-error --location \
    --header "Authorization: Bearer $(get_orcabus_token)" \
    --url "https://metadata.$(get_hostname_from_ssm)/api/v1/library?libraryId=${library_id}" | \
  jq --raw-output \
    '
      .results[0] |
      {
        "libraryId": .libraryId,
        "orcabusId": .orcabusId
      }
    '
}

generate_portal_run_id(){
  echo "$(date -u +'%Y%m%d')$(openssl rand -hex 4)"
}

get_linked_libraries(){
  local library_id="$1"
  local tumor_library_id="${2-}"

  linked_library_obj=$(get_library_obj_from_library_id "$library_id")

  if [ -n "$tumor_library_id" ]; then
    tumor_linked_library_obj=$(get_library_obj_from_library_id "$tumor_library_id")
  else
    tumor_linked_library_obj="{}"
  fi

  jq --null-input --compact-output --raw-output \
    --argjson libraryObj "$linked_library_obj" \
    --argjson tumorLibraryObj "$tumor_linked_library_obj" \
    '
      [
          $libraryObj,
          $tumorLibraryObj
      ] |
      # Filter out empty values, tumorLibraryId is optional
      # Then write back to JSON
      map(select(length > 0))
    '
}


# Generate the event
event_cli_json="$( \
  jq --null-input --raw-output \
    --arg eventBusName "$EVENT_BUS_NAME" \
    --arg detailType "$DETAIL_TYPE" \
    --arg source "$SOURCE" \
    --arg workflowName "${WORKFLOW_NAME}" \
    --arg workflowVersion "${WORKFLOW_VERSION}" \
    --arg payloadVersion "$PAYLOAD_VERSION" \
    --arg portalRunId "$(generate_portal_run_id)" \
    --argjson libraries "$(get_linked_libraries "${LIBRARY_ID}" "${TUMOR_LIBRARY_ID}")" \
    '
      {
        # Standard fields for the event
        "EventBusName": $eventBusName,
        "DetailType": $detailType,
        "Source": $source,
        # Detail must be a JSON object in string format
        "Detail": (
          {
            "status": "DRAFT",
            "timestamp": (now | todateiso8601),
            "workflowName": $workflowName,
            "workflowVersion": $workflowVersion,
            "workflowRunName": ("umccr--automated--" + $workflowName + "--" + ($workflowVersion | gsub("\\."; "-")) + "--" + $portalRunId),
            "portalRunId": $portalRunId,
            "linkedLibraries": $libraries,
          } |
          tojson
        )
      } |
      # Now wrap into an "entry" for the CLI
      {
        "Entries": [
          .
        ]
      }
    ' \
)"

aws events put-events --no-cli-pager --cli-input-json "${event_cli_json}"
```

</details>

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

* We upload the complete draft schema to the AWS Schemas registry,
  this is used to validate a draft event before it is allowed to mature into a READY event

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

**Dragen WGTS DNA Draft to Completed Draft State Machine**

From the dragen WGTS DNA DRAFT event, we populate all inputs to make another draft event, complete with all required
inputs.

![draft-to-completed-draft-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-complete-draft-schema.svg)

**Dragen WGTS DNA Validate Draft and Put Ready Event**

Take in a dragen WGTS DNA DRAFT event, make sure it's valid, and then generate a READY event for the dragen WGTS DNA
pipeline.

![validate-draft-and-put-ready-event-state-machine](docs/workflow-studio-exports/dragen-wgts-dna-validate-draft-and-put-ready-event.svg)

**Dragen WGTS DNA Ready to ICAv2 WES Submitted State Machine**

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

For general terms and expressions used across OrcaBus services, please see the
platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).
