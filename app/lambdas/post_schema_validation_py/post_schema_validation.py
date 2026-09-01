#!/usr/bin/env python3

"""
Confirm that the data uris in the inputs and engine parameters are appropriate
"""
# Imports
from pathlib import Path
from typing import Dict, Tuple, TypedDict, List, Any
import logging
from os import environ
from time import sleep
from urllib.parse import urlparse

# Wrapica imports
from libica.openapi.v3 import ApiException
from wrapica.project_data import coerce_data_id_or_uri_to_project_data_obj, get_project_data_obj_by_id
from wrapica.storage_configuration import get_s3_key_prefix_by_project_id
from wrapica.project_pipelines import get_project_pipeline_obj
from wrapica.project import get_project_obj_from_project_id

# Layer imports
from orcabus_api_tools.workflow import add_comment_to_workflow_run, get_workflow_run
from orcabus_api_tools.metadata import get_library_from_library_id
from orcabus_api_tools.filemanager import get_s3_object_id_from_s3_uri, list_files_recursively
from orcabus_api_tools.filemanager.errors import S3FileNotFoundError
from icav2_tools import set_icav2_env_vars

# Globals
WORKFLOW_NAME_ENV_VAR = "WORKFLOW_NAME"
TEST_BUCKET_ENV_VAR = "TEST_DATA_BUCKET_NAME"
REF_DATA_BUCKET_ENV_VAR = "REF_DATA_BUCKET_NAME"
# Get test / ref env var values
TEST_BUCKET = environ[TEST_BUCKET_ENV_VAR]
REF_DATA_BUCKET = environ[REF_DATA_BUCKET_ENV_VAR]
# Get workflow env vars as values
WORKFLOW_NAME = environ[WORKFLOW_NAME_ENV_VAR]
COMMENT_AUTHOR = f"{WORKFLOW_NAME}-workflow-validation-service"
# Coverage env vars
MIN_RAW_TUMOR_WGS_COVERAGE_ENV_VAR = 'MIN_RAW_TUMOR_WGS_COVERAGE'
MIN_DEDUP_TUMOR_WGS_COVERAGE_ENV_VAR = 'MIN_DEDUP_TUMOR_WGS_COVERAGE'
MIN_RAW_NORMAL_WGS_COVERAGE_ENV_VAR = 'MIN_RAW_NORMAL_WGS_COVERAGE'
MIN_DEDUP_NORMAL_WGS_COVERAGE_ENV_VAR = 'MIN_DEDUP_NORMAL_WGS_COVERAGE'
# Get coverage env var values
MIN_RAW_TUMOR_WGS_COVERAGE = int(environ[MIN_RAW_TUMOR_WGS_COVERAGE_ENV_VAR])
MIN_DEDUP_TUMOR_WGS_COVERAGE = int(environ[MIN_DEDUP_TUMOR_WGS_COVERAGE_ENV_VAR])
MIN_RAW_NORMAL_WGS_COVERAGE = int(environ[MIN_RAW_NORMAL_WGS_COVERAGE_ENV_VAR])
MIN_DEDUP_NORMAL_WGS_COVERAGE = int(environ[MIN_DEDUP_NORMAL_WGS_COVERAGE_ENV_VAR])
# Midfixes
ANALYSIS_MIDFIXES = ["analysis", "output", "outputs"]
LOGS_MIDFIX = "logs"
# Clinical workflow name
CLINICAL_WORKFLOW_NAME = 'clinical'
AUTOMATED_WORKFLOW_PREFIX = "umccr--automated"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Comment formatting constants
MAX_COMMENT_LENGTH = 1024
TRUNCATION_SUFFIX = "\n... [truncated, see execution ARN for full detail]"


def _format_comment_with_arn(body: str, execution_arn: str) -> str:
    """
    Append the execution ARN footer to a comment and enforce the 1024 char limit.
    """
    footer = f"---\nStep Functions Execution: {execution_arn}"
    full_comment = f"{body}\n{footer}"

    if len(full_comment) > MAX_COMMENT_LENGTH:
        available = MAX_COMMENT_LENGTH - len(footer) - len(TRUNCATION_SUFFIX) - 1
        full_comment = f"{body[:available]}{TRUNCATION_SUFFIX}\n{footer}"

    return full_comment


class PreLaunchSomaticTags(TypedDict):
    """
    Launch tags we can expect when running the workflow in somatic mode
    """
    # Metadata
    libraryId: str
    tumorLibraryId: str
    subjectId: str
    individualId: str
    # Readsets
    fastqRgidList: List[str]
    tumorFastqRgidList: List[str]
    # Fingerprint checking
    ntsmExternalPassing: bool
    ntsmInternalPassing: bool
    tumorNtsmInternalPassing: bool
    # Normal pre-launch estimates
    preLaunchDupFracEst: float
    preLaunchCoverageEst: float
    preLaunchInsertSizeEst: float
    # Tumor pre-launch estimates
    tumorPreLaunchDupFracEst: float
    tumorPreLaunchCoverageEst: float
    tumorPreLaunchInsertSizeEst: float


def validate_engine_parameters(
        engine_parameters: Dict,
        workflow_run_id: str,
        project_prefix: str
) -> Tuple[bool, List[str]]:
    """
    Validate the engine parameters.
    :param engine_parameters: The engine parameters to validate.
    :param workflow_run_id: The workflow run ID
    :param project_prefix: The project prefix
    :return: A tuple of (is_valid, list of failure comments)
    """
    failures: List[str] = []

    # Get the project id
    project_id = engine_parameters.get("projectId")

    # Assert project id is set and resolves to a valid ICAv2 project
    if project_id is None:
        failures.append("projectId is not set")
        return False, failures
    try:
        get_project_obj_from_project_id(project_id)
    except ApiException:
        failures.append(f"Cannot find project id {project_id}")
        return False, failures

    # Get URIs
    output_uri = engine_parameters.get("outputUri", "")
    logs_uri = engine_parameters.get("logsUri", "")
    pipeline_id = engine_parameters.get("pipelineId", "")

    # Validate the URIs start with the project prefix
    if not output_uri.startswith(project_prefix):
        failures.append(f"outputUri '{output_uri}' is not in the project context '{project_prefix}'")
    if not logs_uri.startswith(project_prefix):
        failures.append(f"logsUri '{logs_uri}' is not in the project context '{project_prefix}'")

    # Get the portal run id from the workflow run id
    portal_run_id = get_workflow_run(workflow_run_id)['portalRunId']

    # Validate outputUri ends with /<analysis-midfix>/<workflow-name>/<portal-run-id>/
    output_uri_valid = any(
        output_uri.endswith(f"/{midfix}/{WORKFLOW_NAME}/{portal_run_id}/")
        for midfix in ANALYSIS_MIDFIXES
    )
    if not output_uri_valid:
        valid_suffixes = ", ".join(
            f"/{midfix}/{WORKFLOW_NAME}/{portal_run_id}/" for midfix in ANALYSIS_MIDFIXES
        )
        failures.append(
            f"outputUri '{output_uri}' does not end with a valid suffix. "
            f"Expected one of: {valid_suffixes}"
        )

    # Validate logsUri ends with /logs/<workflow-name>/<portal-run-id>/
    if not logs_uri.endswith(f"/{LOGS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}/"):
        failures.append(
            f"logsUri '{logs_uri}' does not end with '/{LOGS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}/'"
        )

    # Confirm the pipeline is accessible in the project
    try:
        _ = get_project_pipeline_obj(
            project_id=project_id,
            pipeline_id=pipeline_id,
        )
    except ValueError:
        failures.append(f"The pipeline {pipeline_id} cannot be found in the project {project_id}")

    if failures:
        return False, failures
    return True, []


def validate_inputs(
        inputs: Dict,
        project_id: str,
        project_prefix: str,
) -> Tuple[bool, List[str]]:
    """
    Validate the inputs.

    Performs two-phase validation:
    1. Filemanager existence check — confirms file/folder URIs exist at the S3 level
       (excludes reference data bucket URIs since they are not indexed by the Filemanager)
    2. ICA project context check — confirms URIs outside of ref/test/project-prefix
       are linked to the project

    :param inputs: The inputs to validate.
    :param project_id: The ICAv2 project id to validate against.
    :param project_prefix: The ICAv2 project prefix
    :return: A tuple of (is_valid, list of failure comments)
    """
    failures: List[str] = []

    # Get all data uris from the inputs
    data_uris = []
    for key in ["sequenceData", "tumorSequenceData"]:
        for fastq_obj in inputs.get(key, {}).get("fastqListRows", []):
            # We filter out 'None' values later
            data_uris.extend([
                fastq_obj.get("read1FileUri"),
                fastq_obj.get("read2FileUri")
            ])

    # We may also have:
    # reference.tarball
    # somaticReference.tarball
    # oraReference
    for ref_key in ["reference", "somaticReference"]:
        ref_obj = inputs.get(ref_key, {})
        data_uris.append(ref_obj.get("tarball"))
    data_uris.append(inputs.get("oraReference"))

    # Remove empty / None values from list
    data_uris = [uri for uri in data_uris if uri]

    # Phase 1: Filemanager existence check — ALL URIs except refdata bucket
    # This confirms every input file/folder actually exists at the S3 level,
    # regardless of which bucket it's in.
    non_reference_data_uris = list(filter(
        lambda uri: not uri.startswith(f"s3://{REF_DATA_BUCKET}/"),
        data_uris
    ))
    for data_uri in non_reference_data_uris:
        # Check if it's a folder URI (ends with /)
        if data_uri.endswith("/"):
            # For folder URIs, verify at least 1 file exists under that prefix
            if not (
                    len(
                        list_files_recursively(
                            urlparse(data_uri).netloc,
                            (str(Path(urlparse(data_uri).path)).lstrip("/") + "/")
                        )
                    ) > 0
            ):
                failures.append(
                    f"Folder URI '{data_uri}' has no files found under that prefix in the Filemanager"
                )
        else:
            # For file URIs, confirm the file exists
            try:
                get_s3_object_id_from_s3_uri(data_uri)
            except S3FileNotFoundError:
                failures.append(
                    f"Data URI '{data_uri}' cannot be found by the Filemanager, are you sure it exists?"
                )

    # If Filemanager checks failed, return early
    if failures:
        return False, failures

    # Phase 2: ICA project context validation
    # Only URIs outside ref/test/project-prefix need ICA project linking confirmed
    uris_to_validate = list(filter(
        lambda uri: not (
                uri.startswith(f"s3://{REF_DATA_BUCKET}/") or
                uri.startswith(f"s3://{TEST_BUCKET}/") or
                uri.startswith(project_prefix)
        ),
        data_uris
    ))

    # Validate each URI is accessible in the project context
    for data_uri in uris_to_validate:
        # Try get the icav2 object by uri
        try:
            project_data_obj = coerce_data_id_or_uri_to_project_data_obj(
                data_id_or_uri=data_uri,
            )
        except ValueError:
            failures.append(f"Data URI '{data_uri}' cannot be found in the project context '{project_id}'")
            continue

        # Then try get it in this context
        try:
            get_project_data_obj_by_id(
                project_id=project_id,
                data_id=project_data_obj.data.id
            )
        except ApiException:
            failures.append(f"Data URI '{data_uri}' cannot be found in the project context '{project_id}'")

    if failures:
        return False, failures
    return True, []


def validate_clinical_input_metrics(
        inputs: Dict[str, Any],
        tags: PreLaunchSomaticTags,
        invalidate_on_failure: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Perform the following checks on the input tags to ensure we are running the appropriate analysis

    1. ntsmInternalPassing / tumorNtsmInternalPassing pass
    2. ntsmExternalPassing passes
    3. Raw germline coverage is above 30X and deduplicated coverage is above 25X
    4. Raw tumor coverage is above 60X and deduplicated coverage is above 50X
    """
    # Initialise is_valid
    is_valid = True
    comments = []

    # 1. Fingerprint checks
    if (
            len(inputs.get("sequenceData", {}).get("fastqListRows", [])) > 1 and
            not tags.get('ntsmInternalPassing')
    ):
        is_valid = False
        comments.append("Normal internal fingerprint failed")
    if (
            len(inputs.get("tumorSequenceData", {}).get("fastqListRows", [])) > 1 and
            not tags.get('tumorNtsmInternalPassing')
    ):
        is_valid = False
        comments.append("Tumor internal fingerprint failed")
    # 2. Cross fingerprint checks
    if not tags['ntsmExternalPassing']:
        is_valid = False
        comments.append("Fingerprints between tumor & normal did not match")

    # 3. Germline coverage checks
    if tags['preLaunchCoverageEst'] < MIN_RAW_NORMAL_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Normal did not meet raw threshold coverage of {MIN_RAW_NORMAL_WGS_COVERAGE} X")
    if (tags['preLaunchCoverageEst'] * (1 - tags['preLaunchDupFracEst'])) < MIN_DEDUP_NORMAL_WGS_COVERAGE:
        # is_valid = False  # Temp comment out
        comments.append(f"Warning: Normal deduplicated coverage estimate did not meet {MIN_DEDUP_NORMAL_WGS_COVERAGE} X")
    # 4. Somatic coverage checks
    if tags['tumorPreLaunchCoverageEst'] < MIN_RAW_TUMOR_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Tumor did not meet raw threshold coverage of {MIN_RAW_TUMOR_WGS_COVERAGE} X")
    if (tags['tumorPreLaunchCoverageEst'] * (1 - tags['tumorPreLaunchDupFracEst'])) < MIN_DEDUP_TUMOR_WGS_COVERAGE:
        # is_valid = False  # Temp comment out
        comments.append(f"Warning: Tumor deduplicated coverage estimate did not meet {MIN_DEDUP_TUMOR_WGS_COVERAGE} X")

    # Don't worry about failing an invalid run here
    # But we want the comments regardless
    if not invalidate_on_failure:
        return True, comments

    return is_valid, comments


def handler(event, context) -> Dict[str, bool]:
    """
    Given a draft schema, validate it against the current schema and print the results.
    :return:
    """
    # We have a valid schema, lets confirm that the fastq uris are valid uris and in the appropriate project context
    # Set env vars
    set_icav2_env_vars()

    # Get the event data
    payload_data = event.get('data')
    workflow_run_id = event.get("workflowRunId", "")
    execution_arn = event.get("executionArn", "")

    # Get the ICAv2 project id from the event
    engine_parameters = payload_data.get("engineParameters", {})
    tags = payload_data.get("tags", {})

    # Get the project prefix
    project_id = engine_parameters.get("projectId")
    if project_id is None:
        add_comment_to_workflow_run(
            workflow_run_orcabus_id=workflow_run_id,
            comment=_format_comment_with_arn(
                "Post schema validation failed: projectId is not set",
                execution_arn
            ),
            author=COMMENT_AUTHOR
        )
        return {"isValid": False}

    try:
        project_prefix = get_s3_key_prefix_by_project_id(project_id)
    except ApiException:
        add_comment_to_workflow_run(
            workflow_run_orcabus_id=workflow_run_id,
            comment=_format_comment_with_arn(
                f"Post schema validation failed: cannot resolve S3 key prefix for projectId '{project_id}'",
                execution_arn
            ),
            author=COMMENT_AUTHOR
        )
        return {"isValid": False}

    if project_prefix is None:
        add_comment_to_workflow_run(
            workflow_run_orcabus_id=workflow_run_id,
            comment=_format_comment_with_arn(
                f"Post schema validation failed: no S3 key prefix configured for projectId '{project_id}'",
                execution_arn
            ),
            author=COMMENT_AUTHOR
        )
        return {"isValid": False}

    # Collect all failures (hard failures that invalidate the run) and
    # notes (informational comments that do not invalidate the run)
    all_failures: List[str] = []
    notes: List[str] = []

    # Get the inputs and confirm that the fastq uris are valid
    # and are accessible in the right project context
    inputs = payload_data.get("inputs")

    # Validate the engine parameters
    is_valid, failures = validate_engine_parameters(
        engine_parameters,
        workflow_run_id=workflow_run_id,
        project_prefix=project_prefix,
    )
    all_failures.extend(failures)

    # Validate the inputs (only if engine params are valid — we need project context)
    if is_valid:
        is_valid, failures = validate_inputs(
            inputs,
            project_id=project_id,
            project_prefix=project_prefix
        )
        all_failures.extend(failures)

    # Check if this is a clinical sample and if we
    # need to hold off until coverage matches
    if is_valid:
        tumor_library_id = tags.get("tumorLibraryId", None)
        # Germline only run
        if tumor_library_id is None:
            pass
        # Not a clinical sample
        # Or not an automated run — collect coverage comments as notes only
        elif (
                not get_library_from_library_id(tumor_library_id)['workflow'] == CLINICAL_WORKFLOW_NAME or
                not get_workflow_run(workflow_run_id)["workflowRunName"].startswith(AUTOMATED_WORKFLOW_PREFIX)
        ):
            _, clinical_comments = validate_clinical_input_metrics(
                inputs,
                tags,
                invalidate_on_failure=False
            )
            notes.extend(clinical_comments)
        # Automated Clinical TN Sample — coverage comments are hard failures
        else:
            clinical_valid, clinical_comments = validate_clinical_input_metrics(
                inputs,
                tags,
                invalidate_on_failure=True
            )
            if not clinical_valid:
                all_failures.extend(clinical_comments)
            else:
                notes.extend(clinical_comments)

    # Somewhere along the way, the validation failed
    if all_failures:
        if len(all_failures) == 1:
            add_comment_to_workflow_run(
                workflow_run_orcabus_id=workflow_run_id,
                comment=_format_comment_with_arn(
                    f"Post schema validation failed: {all_failures[0]}",
                    execution_arn
                ),
                author=COMMENT_AUTHOR
            )
        else:
            add_comment_to_workflow_run(
                workflow_run_orcabus_id=workflow_run_id,
                comment=_format_comment_with_arn(
                    f"Post schema validation failed for {len(all_failures)} reasons",
                    execution_arn
                ),
                author=COMMENT_AUTHOR
            )
            for idx, failure in enumerate(all_failures, start=1):
                add_comment_to_workflow_run(
                    workflow_run_orcabus_id=workflow_run_id,
                    comment=_format_comment_with_arn(
                        f"Reason {idx} of {len(all_failures)}: {failure}",
                        execution_arn
                    ),
                    author=COMMENT_AUTHOR
                )
                sleep(1)
        return {
            "isValid": False
        }

    # Validation passed — write any informational notes
    if notes:
        for idx, note in enumerate(notes, start=1):
            add_comment_to_workflow_run(
                workflow_run_orcabus_id=workflow_run_id,
                comment=_format_comment_with_arn(
                    f"Post schema validation note {idx} of {len(notes)}: {note}",
                    execution_arn
                ),
                author=COMMENT_AUTHOR
            )
            sleep(1)

    # Ensure that we comment if downsampling has been added
    if payload_data.get("inputs", {}).get("somaticAlignmentOptions", {}).get("enableFractionalDownSampler"):
        comment = "Downsampling has been turned on for this workflow run"
        if payload_data.get("inputs", {}).get("somaticAlignmentOptions", {}).get(
                "downSamplerTumorSubsample") is not None:
            comment += ' - tumor has been downsampled to {}'.format(
                payload_data.get("inputs", {}).get("somaticAlignmentOptions", {}).get("downSamplerTumorSubsample")
            )
        if payload_data.get("inputs", {}).get("somaticAlignmentOptions", {}).get(
                "downSamplerNormalSubsample") is not None:
            comment += ' - normal has been downsampled to {}'.format(
                payload_data.get("inputs", {}).get("somaticAlignmentOptions", {}).get("downSamplerNormalSubsample")
            )
        add_comment_to_workflow_run(
            workflow_run_orcabus_id=workflow_run_id,
            comment=_format_comment_with_arn(comment, execution_arn),
            author=COMMENT_AUTHOR
        )

    return {
        "isValid": True
    }
