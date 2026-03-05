#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Globals
LAMBDA_FUNCTION_NAME="WruDraftValidator"
HOSTNAME=""

# CLI Defaults
FORCE=false  # Use --force to set to true
OUTPUT_URI_PREFIX=""
LOGS_URI_PREFIX=""
PROJECT_ID=""
DISABLE_SV_CALLING="false"
COMMENT=""  # Use -c or --comment to set a comment to be added to the payload
SAVE_DRAFT_PAYLOAD=""

# Workflow constants
WORKFLOW_NAME="dragen-wgts-dna"
WORKFLOW_VERSION="4.4.4"
EXECUTION_ENGINE="ICA"
CODE_VERSION="724101a"
PAYLOAD_VERSION="2025.06.24"

# SOP constants
THIS_SCRIPT_VERSION="2026.03.05"
SOP_ID="PM.DWD.1"
GITHUB_REPO="OrcaBus/service-dragen-wgts-dna-pipeline-manager"
THIS_SCRIPT_PATH="docs/operation/SOP/${SOP_ID}/generate-WRU-draft.sh"

# Library ID array
LIBRARY_ID_ARRAY=()

# AWS Account ID by prefix
declare -A PREFIX_BY_AWS_ACCOUNT_ID=(
  ["843407916570"]="dev"
  ["455634345446"]="stg"
  ["472057503814"]="prod"
)
declare -A COGNITO_USER_POOL_ID_BY_PREFIX=(
  ["ap-southeast-2_iWOHnsurL"]="dev"
  ["ap-southeast-2_wWDrdTyzP"]="stg"
  ["ap-southeast-2_HFrQ3aWm8"]="prod"
)

# Functions
echo_stderr(){
  echo "$(date -Iseconds)" "$@" >&2
}

print_usage(){
  : '
  Print usage
  '
  local hostname
  hostname="$(get_hostname_from_ssm)"
  if [[ -z "${hostname}" ]]; then
    hostname="<aws_account_prefix>.umccr.org"
  fi

  echo "
generate-WRU-draft.sh [-h | --help]
generate-WRU-draft.sh (library_id)...
                      (-c | --comment <comment>)
                      [-f | --force]
                      [-o | --output-uri-prefix <s3_uri>]
                      [-l | --logs-uri-prefix <s3_uri>]
                      [-p | --project-id <project_id>]
                      [--save-draft-payload <output_file>]
                      [--workflow-version <workflow_version>]
                      [--code-version <code_version>]
                      [--disable-sv-calling]

Description:
Run this script to generate a draft WorkflowRunUpdate event for the specified library IDs.

Positional arguments:
  library_id:   One or more library IDs to link to the WorkflowRunUpdate event.

Keyword arguments:
  -h | --help:               Print this help message and exit.
  -c | --comment:            (Required) A comment to add to the payload, which will be visible in the workflow run details in OrcaUI.
  -f | --force:              (Optional) Don't confirm before pushing the event to EventBridge.
  -l | --logs-uri-prefix:    (Optional) S3 URI for logs (must end with a slash).
  -o | --output-uri-prefix:  (Optional) S3 URI for outputs (must end with a slash).
  -p | --project-id:         (Optional) ICAv2 Project ID to associate with the workflow run
  --save-draft-payload:      (Optional) Save the generated draft event to a local file after pushing to event bridge for record purposes.
  --workflow-version:        (Optional) The workflow version to use, defaults to ${WORKFLOW_VERSION},
                             but can also be set to 4.4.6, this is particularly useful for SV calling.
  --code-version:            (Optional) Set the code version to pull a particular workflow object.
                             Required if using a workflow version other than the default.
  --disable-sv-calling:      (Optional) Disable structural variant calling for the somatic step of the pipeline.

Environment:
  PORTAL_TOKEN: (Required) Your personal portal token from https://portal.${hostname}/
  AWS_PROFILE:  (Optional) The AWS CLI profile to use for authentication.
  AWS_REGION:   (Optional) The AWS region to use for AWS CLI commands.

Binaries:
  - aws CLI should be installed and configured with appropriate credentials and region.
  - jq should be installed for JSON parsing.
  - curl should be installed for making API requests.
  - base64 should be available for decoding the portal token.
  - openssl should be available for generating random portal run ids.

Example usage:
bash generate-WRU-draft.sh tumor_library_id normal_library_id
bash generate-WRU-draft.sh tumor_library_id normal_library_id \\
  --comment 'Redriving analysis after failure' \\
  --output-uri-prefix s3://project-bucket/analysis/dragen-wgts-dna/ \\
  --logs-uri-prefix s3://project-bucket/logs/dragen-wgts-dna \\
  --project-id project-uuid-1234-abcd \\
  --save-draft-payload tumor_library_id__normal_library_id__draft_payload.json
"
}

compare_script_version_to_repo(){
  : '
  Compare the version of this script to the version in the repo, and print a warning if they are different
  '
  repo_script_version="$( \
    curl --silent --fail --location --show-error \
      --url "https://raw.githubusercontent.com/${GITHUB_REPO}/refs/heads/main/${THIS_SCRIPT_PATH}" 2>/dev/null | \
    (
      grep -m1 "THIS_SCRIPT_VERSION" | \
      cut -d'"' -f2
    ) || echo "unknown"
  )"

  if [[ "${THIS_SCRIPT_VERSION}" != "${repo_script_version}" ]]; then
    echo_stderr "Warning: This script version (${THIS_SCRIPT_VERSION}) is different from the version in the repo (${repo_script_version})."
    echo_stderr "Warning: Consider refetching this script from https://github.com/${GITHUB_REPO}/blob/main/${THIS_SCRIPT_PATH}"
  fi
}

get_email_from_portal_token(){
  : '
  Get the email to use from the portal JWT
  We use this to make a comment on the workflow run in the OrcaUI
  once the event is pushed to EventBridge and the workflow run is created,
  to indicate who created the workflow run
  '
  cut -d'.' -f2 <<< "${PORTAL_TOKEN}" | \
    (base64 --decode 2>/dev/null || true) | \
  jq --raw-output '.email'
}

get_hostname_from_ssm(){
  : '
  Get the hostname from SSM Parameter Store
  '
  # Cache the hostname in a global variable to
  # avoid multiple calls to SSM Parameter Store
  if [[ -n "${HOSTNAME}" ]]; then
  echo "${HOSTNAME}"
  return
  fi

  # Get the hostname from SSM Parameter Store and
  # cache it in the HOSTNAME global variable
  aws ssm get-parameter \
    --name "/hosted_zone/umccr/name" \
    --output json | \
  jq --raw-output \
    '.Parameter.Value'
}

get_library_obj_from_library_id(){
  : '
  Get the library object (libraryId and orcabusId) from the library id
  '
  local library_id="$1"
  curl --silent --fail --show-error --location \
    --header "Authorization: Bearer ${PORTAL_TOKEN}" \
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
  for library_id in "${LIBRARY_ID_ARRAY[@]}"; do
    get_library_obj_from_library_id "${library_id}"
  done | \
  jq --slurp --raw-output --compact-output
}

get_lambda_function_name(){
  aws lambda list-functions \
    --output json \
    --query "Functions" | \
  jq --raw-output --compact-output \
    --arg functionName "${LAMBDA_FUNCTION_NAME}" \
    '
      map(select(.FunctionName | contains($functionName))) |
      .[0].FunctionName
    '
}

get_workflow(){
  local workflow_name="$1"
  local workflow_version="$2"
  local execution_engine="$3"
  local code_version="$4"
  curl --silent --fail --show-error --location \
    --request GET \
    --get \
    --header "Authorization: Bearer ${PORTAL_TOKEN}" \
    --url "https://workflow.$(get_hostname_from_ssm)/api/v1/workflow" \
    --data "$( \
      jq \
       --null-input --compact-output --raw-output \
       --arg workflowName "$workflow_name" \
       --arg workflowVersion "$workflow_version" \
       --arg executionEngine "$execution_engine" \
       --arg codeVersion "$code_version" \
       '
         {
            "name": $workflowName,
            "version": $workflowVersion,
            "executionEngine": $executionEngine,
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

get_workflow_run(){
  local portal_run_id="$1"

  curl --silent --fail --show-error --location \
    --request GET \
    --get \
    --header "Authorization: Bearer ${PORTAL_TOKEN}" \
    --url "https://workflow.$(get_hostname_from_ssm)/api/v1/workflowrun?portalRunId=${portal_run_id}" | \
  jq --compact-output --raw-output \
    '
      if (.results | length) > 0 then
        .results[0]
      else
        empty
      end
    '
}

get_aws_account_prefix(){
  local aws_account_id
  aws_account_id="$( \
    aws sts get-caller-identity --output json --query "Account" | \
    jq --raw-output \
  )"
  echo "${PREFIX_BY_AWS_ACCOUNT_ID[${aws_account_id}]:-"unknown_aws_account_prefix"}"
}

get_cognito_user_pool_id(){
  local cognito_user_pool_id
  cognito_user_pool_id="$( \
    cut -d'.' -f2 <<< "${PORTAL_TOKEN}" |
    (base64 --decode 2>/dev/null || true) | \
    jq --raw-output \
      '
        .iss |
        split("/")[-1]
      ' \
  )"
  echo "${COGNITO_USER_POOL_ID_BY_PREFIX[${cognito_user_pool_id}]:-"unknown_cognito_user_pool_id"}"
}

# Get args
while [[ $# -gt 0 ]]; do
  case "$1" in
    # Help
    -h|--help)
      print_usage
      exit 0
      ;;
    # Comment
    -c|--comment)
      COMMENT="$2"
      shift 2
      ;;
    -c=*|--comment=*)
      COMMENT="${1#*=}"
      shift
    ;;
    # Force boolean
    -f|--force)
      FORCE=true
      shift
      ;;
    --save-draft-payload)
      SAVE_DRAFT_PAYLOAD="$2"
      shift 2
      ;;
    --save-draft-payload=*)
      SAVE_DRAFT_PAYLOAD="${1#*=}"
      shift
      ;;
    # Disable SV calling
    --disable-sv-calling)
      DISABLE_SV_CALLING="true"
      shift
    ;;
    # Output URI prefix
    -o|--output-uri-prefix)
      OUTPUT_URI_PREFIX="$2"
      shift 2
    ;;
    -o=*|--output-uri-prefix=*)
      OUTPUT_URI_PREFIX="${1#*=}"
      shift
      ;;
    # Log URI prefix
    -l|--logs-uri-prefix)
      LOGS_URI_PREFIX="$2"
      shift 2
      ;;
    -l=*|--logs-uri-prefix=*)
      LOGS_URI_PREFIX="${1#*=}"
      shift
      ;;
    # Project ID
    -p|--project-id)
      PROJECT_ID="$2"
      shift 2
      ;;
    -p=*|--project-id=*)
      PROJECT_ID="${1#*=}"
      shift
      ;;
    # Workflow version
    --workflow-version)
      WORKFLOW_VERSION="$2"
      shift 2
      ;;
    --workflow-version=*)
      WORKFLOW_VERSION="${1#*=}"
      shift
      ;;
    # Code version
    --code-version)
      CODE_VERSION="$2"
      shift 2
      ;;
    --code-version=*)
      CODE_VERSION="${1#*=}"
      shift
      ;;
    # Positional arguments (library IDs)
      *)
      LIBRARY_ID_ARRAY+=("$1")
      shift
      ;;
  esac
done

# Check required environment variables
if [[ -z "${PORTAL_TOKEN:-}" ]]; then
  echo_stderr "Error: PORTAL_TOKEN environment variable is not set. Exiting."
  print_usage
  exit 1
fi

# Check comment is provided
if [[ -z "${COMMENT}" ]]; then
  echo_stderr "Error: Comment is required. Please provide a comment using the -c or --comment flag. Exiting."
  print_usage
  exit 1
fi

# Check save draft file path is valid if provided
if [[ -n "${SAVE_DRAFT_PAYLOAD}" ]]; then
  # Check parent directory exists
  if [[ ! -d "$(dirname "${SAVE_DRAFT_PAYLOAD}")" ]]; then
    echo_stderr "Error: The parent directory for the file path provided for --save-draft-payload '${SAVE_DRAFT_PAYLOAD}' does not exist."
    echo_stderr "does not exist. Please provide a valid file path with an existing parent directory. Exiting."
    exit 1
  fi
  if [[ -e "${SAVE_DRAFT_PAYLOAD}" ]]; then
    echo_stderr "Error: The file path provided for --save-draft-payload already exists. "
    echo_stderr "Please provide a file path that does not already exist to avoid overwriting. Exiting."
    exit 1
  fi
fi

# Check AWS CLI configuration
if ! aws sts get-caller-identity --output json > /dev/null 2>&1; then
  echo_stderr "Error: AWS CLI is not configured properly. Please configure your AWS CLI with appropriate credentials and region. Exiting."
  exit 1
fi

# Set hostname
HOSTNAME="$(get_hostname_from_ssm)"

# Check script version
compare_script_version_to_repo

# Confirm that the aws account id associated with the credentials
# Matches the cognito user pool id associated with the portal token,
# to help catch users who have multiple AWS profiles configured and are using the wrong one
if [[ "$(get_aws_account_prefix)" != "$(get_cognito_user_pool_id)" ]]; then
  echo_stderr "Warning: The AWS account prefix associated with your AWS credentials ($(get_aws_account_prefix)) "
  echo_stderr "does not match the expected prefix for the portal token you provided ($(get_cognito_user_pool_id))."
  echo_stderr "This may cause API calls to fail due to authentication issues."
  echo_stderr "Please check that you are using the correct AWS profile and that your portal token is valid."
fi

# Generate the portal run id
portal_run_id="$(generate_portal_run_id)"
echo_stderr "Generated Portal Run ID: ${portal_run_id}"

# Get the workflow object
workflow="$( \
  get_workflow \
    "${WORKFLOW_NAME}" "${WORKFLOW_VERSION}" \
    "${EXECUTION_ENGINE}" "${CODE_VERSION}"
)"
echo_stderr "Using workflow: $(jq --raw-output '.orcabusId' <<< "${workflow}")"

# Collecting relevant libraries
echo_stderr "Collecting libraries from metadata manager"
libraries="$(get_linked_libraries)"
# libraries are a list of objects with libraryId and orcabusId fields
# Ensure no object in the list is empty
if [[ -z "${libraries}" || "$(jq 'length' <<< "${libraries}")" == 0 ]]; then
  echo_stderr "Error: No valid libraries found for the provided library IDs. Exiting."
  exit 1
elif [[ "$(jq 'map(select(.libraryId == null or .orcabusId == null)) | length' <<< "${libraries}")" -gt 0 ]]; then
  echo_stderr "Error: One or more library objects are null. Please check the provided library IDs. Exiting."
  exit 1
else
  echo_stderr "Found $(jq 'length' <<< "${libraries}") linked libraries"
fi

# Get the engine parameters
echo_stderr "Generating engine parameters"
engine_parameters=$( \
  jq --null-input --raw-output --compact-output \
  --arg outputUriPrefix "${OUTPUT_URI_PREFIX}" \
  --arg logsUriPrefix "${LOGS_URI_PREFIX}" \
  --arg projectId "${PROJECT_ID}" \
  --arg portalRunId "${portal_run_id}" \
  '
    # Get the engine parameters
    {
      "outputUri": ( if $outputUriPrefix != "" then ($outputUriPrefix + $portalRunId + "/") else "" end ),
      "logsUri": ( if $logsUriPrefix != "" then ($logsUriPrefix + $portalRunId + "/") else "" end ),
      "projectId": $projectId
    } |
    # Remove empty values
    with_entries(select(.value != ""))
  ' \
)

# Generate the event
lambda_payload="$( \
  jq --null-input --raw-output \
    --argjson workflow "${workflow}" \
    --arg payloadVersion "${PAYLOAD_VERSION}" \
    --arg portalRunId "${portal_run_id}" \
    --argjson libraries "${libraries}" \
    --argjson engineParameters "${engine_parameters}" \
    --argjson disableSvCalling "${DISABLE_SV_CALLING}" \
    '
    {
      "status": "DRAFT",
      "timestamp": (now | todateiso8601),
      "workflow": $workflow,
      "workflowRunName": ("umccr--manual--" + $workflow["name"] + "--" + ($workflow["version"] | gsub("\\."; "-")) + "--" + $portalRunId),
      "portalRunId": $portalRunId,
      "libraries": $libraries,
    } |
    if (
      $disableSvCalling or
      ( ($engineParameters | length) > 0 )
    ) then
      # We have a payload to add
      # So we initialise with a version and an empty data object
      .["payload"] = {
        "version": $payloadVersion,
        "data": {}
      } |
      # Separately edit each of the payload data fields
      # Check if the SV calling is to be disabled
      # And edit inputs.somaticSvCallerOptions if so
      if $disableSvCalling then
        .["payload"]["data"]["inputs"] = {
          "somaticSvCallerOptions": {
            "enableSv": false
          }
        }
      end |
      # Check if there are engine parameters to add
      # And set engineParameters if so
      if ( ($engineParameters | length) > 0 ) then
        .["payload"]["data"]["engineParameters"] = $engineParameters
      end
    end
    ' \
)"

# Confirm before pushing the event
if [[ "${FORCE}" == "false" ]]; then
  echo_stderr "Send the following payload to the lambda object:"
  jq --raw-output <<< "${lambda_payload}" 1>&2
  read -r -p 'Confirm to push this event to EventBridge? (y/n): ' confirm_push
  if [[ ! "${confirm_push}" =~ ^[Yy]$ ]]; then
    echo_stderr "Aborting event push."
    exit 1
  fi
fi

# Saving the draft event to a local file if the --save-draft-payload flag is provided, for record purposes
if [[ -n "${SAVE_DRAFT_PAYLOAD}" ]]; then
  echo_stderr "Saving the generated draft event to ${SAVE_DRAFT_PAYLOAD}"
  jq --raw-output <<< "${lambda_payload}" > "${SAVE_DRAFT_PAYLOAD}"
fi

# Set the trap
trap 'rm -f lambda_data_pipe' EXIT

# Push the event to EventBridge
mkfifo lambda_data_pipe
errors_json="$(mktemp "errors.XXXXXX.json")"
echo_stderr "Pushing the draft event for portalRunId ${portal_run_id} via WRU Validation Lambda Function"
aws lambda invoke \
  --function-name "$(get_lambda_function_name)" \
  --payload "$(jq --compact-output <<< "${lambda_payload}")" \
  --cli-binary-format raw-in-base64-out \
  --no-cli-pager \
  --invocation-type 'RequestResponse' \
  lambda_data_pipe 1>/dev/null & \
jq --raw-output \
  '
  if .statusCode != 200 then
    .body | fromjson
  else
    empty
  end
  ' \
  < lambda_data_pipe \
  > "${errors_json}" & \
wait
rm lambda_data_pipe

# Remove trap
trap - EXIT

# Check if there were any errors returned from the Lambda invocation
if [[ -s "${errors_json}" ]]; then
  echo_stderr "Error pushing event to Lambda Function:"
  jq --raw-output '.' < "${errors_json}" 1>&2
  rm "${errors_json}"
  exit 1
else
  rm "${errors_json}"
fi

# Now wait for the workflow run to be registered by the workflow manager,
# which should be done within a minute or two after pushing the event to EventBridge,
# and get the workflow run object, which contains the Orcabus ID that we will use to link the
# workflow run to the comment we will create in the next step
echo_stderr "Waiting for the workflow run to be registered by the workflow manager"
while :; do
  workflow_run_object="$( \
    get_workflow_run "${portal_run_id}"
  )"

  # Check with the workflow manager for the workflow run object
  if [[ -n "${workflow_run_object}" ]]; then
    workflow_run_orcabus_id="$(jq --raw-output '.orcabusId' <<< "${workflow_run_object}")"
    echo_stderr "Workflow run registered with ID: ${workflow_run_orcabus_id}"
    break
  else
    echo_stderr "Workflow run not yet registered, waiting 10 seconds..."
    sleep 10
  fi
done

echo_stderr "Generating workflow comment"
curl --fail --silent --location --show-error \
  --request "POST" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${PORTAL_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "$(
    jq --null-input --raw-output \
      --arg emailAddress "$(get_email_from_portal_token)" \
      --arg sopId "${SOP_ID}" \
      --arg comment "${COMMENT}" \
      '
        {
          "text": "Pipeline executed manually via SOP \($sopId) -- \($comment)",
          "createdBy": $emailAddress
        }
      '
  )" \
  --url "https://workflow.$(get_hostname_from_ssm)/api/v1/workflowrun/${workflow_run_orcabus_id}/comment/" > /dev/null

echo_stderr "Workflow Run Creation Event complete!"
echo_stderr "Please head to 'https://orcaui.$(get_hostname_from_ssm)/runs/workflow/${workflow_run_orcabus_id}' to track the status of the workflow run"
