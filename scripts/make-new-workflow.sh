#!/usr/bin/env bash

: '
Register a new workflow in the workflow manager
'


help_message="Usage: make-new-workflow.sh
Wrapper script to make a new workflow in the workflow manager

Options:
  -h, --help              Show this help message and exit
  --workflow-name         Required: The workflow name (dragen-wgts-dna)
  --workflow-version      Required: The workflow version
  --execution-engine      Required: The execution engine
  --pipeline-id           Required: The pipeline id on the execution engine
  --codeVersion           Required: The code version
  --validationState       Required: The validation state
"

# FUNCTIONS
echo_stderr(){
  : '
  Write out to stderr
  '
  echo "${@}" 1>&2
}

print_help() {
  echo_stderr "${help_message}"
}

# GLOBALS
HOSTNAME_SSM_PARAMETER_NAME='/hosted_zone/umccr/name'
ORCABUS_TOKEN_SECRET_ID='orcabus/token-service-jwt'

# Get inputs
workflow_name=""
workflow_version=""
execution_engine=""
pipeline_id=""
code_version=""
validation_state=""

while [ $# -gt 0 ]; do
  case "$1" in
    --workflow-name)
	  workflow_name="${2}"
	  shift 2
	  ;;
	--workflow-version)
	  workflow_version="${2}"
	  shift 2
	  ;;
    --execution-engine)
      execution_engine="${2}"
      shift 2
      ;;
    --pipeline-id)
      pipeline_id="${2}"
      shift 2
      ;;
    --code-version)
      code_version="${2}"
      shift 2
      ;;
    --validation-state)
      validation_state="${2}"
	  shift 2
	  ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      print_help
      exit 1
      ;;
  esac
  shift 1
done

# INPUT Checker

# Check the inputs are provided
if [[ -z "${workflow_name}" ]]; then
  echo_stderr "Error: --workflow-name is required"
  print_help
  exit 1
elif [[ -z "${workflow_version}" ]]; then
  echo_stderr "Error: --workflow-version is required"
  print_help
  exit 1
elif [[ -z "${execution_engine}" ]]; then
  echo_stderr "Error: --execution-engine is required"
  print_help
  exit 1
elif [[ -z "${pipeline_id}" ]]; then
  echo_stderr "Error: --pipeline-id is required"
  print_help
  exit 1
elif [[ -z "${code_version}" ]]; then
  echo_stderr "Error: --code-version is required"
  print_help
  exit 1
elif [[ -z "${validation_state}" ]]; then
  echo_stderr "Error: --validation-state is required"
  print_help
  exit 1
fi

# Check the aws cli tool is available
if ! type aws &> /dev/null; then
  echo_stderr "Error: aws cli tool is not installed or not in PATH"
  exit 1
fi

# Check the curl tool is available
if ! type curl &> /dev/null; then
  echo_stderr "Error: curl tool is not installed or not in PATH"
  exit 1
fi

# Check the jq tool is available
if ! type jq &> /dev/null; then
  echo_stderr "Error: jq tool is not installed or not in PATH"
  exit 1
fi

# Check we're logged in to aws
if ! aws sts get-caller-identity &> /dev/null; then
  echo_stderr "Error: could not connect to AWS, please check your AWS credentials"
  exit 1
fi

# Get hostname and orcabus tokens from SSM and Secrets Manager
hosted_zone="$( \
  aws ssm get-parameter \
    --name "${HOSTNAME_SSM_PARAMETER_NAME}" \
	--query 'Parameter.Value' \
	--output text \
)"

orcabus_token="$( \
  aws secretsmanager get-secret-value \
	--secret-id "${ORCABUS_TOKEN_SECRET_ID}" \
	--query 'SecretString' \
	--output json | \
  jq --raw-output \
    '
      fromjson | .id_token
    ' \
)"

curl \
  --fail --silent --location --show-error \
  --request "POST" \
  --header "Accept: application/json" \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer ${orcabus_token}" \
  --data "$( \
    jq --null-input --raw-output --compact-output \
      --arg workflowName "${workflow_name}" \
      --arg workflowVersion "${workflow_version}" \
      --arg executionEngine "${execution_engine}" \
      --arg pipelineId "${pipeline_id}" \
      --arg codeVersion "${code_version}" \
      --arg validationState "${validation_state}" \
      '
      	{
      	  "name": $workflowName,
      	  "version": $workflowVersion,
      	  "executionEngine": $executionEngine,
      	  "executionEnginePipelineId": $pipelineId,
      	  "codeVersion": $codeVersion,
      	  "validationState": $validationState
      	}
      ' \
  )" \
  --url "https://workflow.${hosted_zone}/api/v1/workflow/" | \
jq --raw-output
