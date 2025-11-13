#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Globals
FORCE=false  # Use --force to set to true
EVENT_BUS_NAME="OrcaBusMain"
DETAIL_TYPE="WorkflowRunUpdate"
SOURCE="orcabus.manual"

WORKFLOW_NAME="dragen-wgts-dna"
WORKFLOW_VERSION="4.4.4"
EXECUTION_ENGINE="ICA"
CODE_VERSION="677f34a"

PAYLOAD_VERSION="2025.06.24"

# Library id array
LIBRARY_ID_ARRAY=()

# Functions
echo_stderr(){
  echo "$(date -Iseconds)" "$@" >&2
}

print_usage(){
  echo "
generate-WRU-draft.sh [-h | --help]
generate-WRU-draft.sh [-f | --force] (library_id)...


Description:
Run this script to generate a draft WorkflowRunUpdate event for the specified library IDs.

Options:
  -h | --help:		Print this help message and exit.
  -f | --force:  	Don't confirm before pushing the event to EventBridge.
  library_id ...:	One or more library IDs to include in the event. Repeat as needed.

Environment:
  AWS_PROFILE:  (Optional) The AWS CLI profile to use for authentication.
  AWS_REGION:   (Optional) The AWS region to use for AWS CLI commands.

Example usage:
bash generate-WRU-draft.sh tumor_library_id normal_library_id
"
}

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
  for library_id in "${LIBRARY_ID_ARRAY[@]}"; do
    get_library_obj_from_library_id "${library_id}"
  done | \
  jq --slurp --raw-output --compact-output
}


get_workflow(){
  local workflow_name="$1"
  local workflow_version="$2"
  local execution_engine="$3"
  local code_version="$4"
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

# Get args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--force)
      FORCE=true
      shift
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      LIBRARY_ID_ARRAY+=("$1")
      shift
      ;;
  esac
done

# Generate the portal run id
portal_run_id="$(generate_portal_run_id)"
echo_stderr "Generated portalRunId: ${portal_run_id}"

# Get the workflow object
workflow="$( \
  get_workflow \
	"${WORKFLOW_NAME}" "${WORKFLOW_VERSION}" \
	"${EXECUTION_ENGINE}" "${CODE_VERSION}"
)"
echo_stderr "Using workflow: $(jq --raw-output '.orcabusId' <<< "${workflow}")"

# Generate the event
event_cli_json="$( \
  jq --null-input --raw-output \
    --arg eventBusName "$EVENT_BUS_NAME" \
    --arg detailType "$DETAIL_TYPE" \
    --arg source "$SOURCE" \
    --argjson workflow "${workflow}" \
    --arg payloadVersion "${PAYLOAD_VERSION}" \
    --arg portalRunId "${portal_run_id}" \
    --argjson libraries "$(get_linked_libraries)" \
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

# Confirm before pushing the event
if [[ "${FORCE}" == "false" ]]; then
	echo_stderr "Generated the following WorkflowRunUpdate event draft:"
	jq --raw-output <<< "${event_cli_json}" 1>&2

	read -r -p 'Confirm to push this event to EventBridge? (y/n): ' confirm_push
	if [[ ! "${confirm_push}" =~ ^[Yy]$ ]]; then
	  echo_stderr "Aborting event push."
	  exit 1
	fi
fi

# Push the event to EventBridge
echo_stderr "Pushing the draft event for portalRunId ${portal_run_id} to the EventBridge"
aws events put-events \
  --no-cli-pager \
  --cli-input-json "$( \
  	jq --raw-output \
  	  '
  	    ( .Detail = (.Detail | tojson) ) |
  	    {
		  "Entries": [ . ]
	    }
  	  ' <<< "${event_cli_json}" \
  )"
