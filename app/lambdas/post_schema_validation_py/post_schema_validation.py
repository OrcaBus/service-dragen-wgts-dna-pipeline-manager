#!/usr/bin/env python3

"""
Confirm that the data uris in the inputs and engine parameters are appropriate
"""

# Imports
from typing import Dict, Tuple, cast, TypedDict, List
import logging
from os import environ
from time import sleep

# Wrapica imports
from libica.openapi.v3 import ApiException
from wrapica.project_data import coerce_data_id_or_uri_to_project_data_obj, get_project_data_obj_by_id
from wrapica.storage_configuration import get_s3_key_prefix_by_project_id
from wrapica.project_pipelines import get_project_pipeline_obj
from wrapica.project import get_project_obj_from_project_id

# Layer imports
from orcabus_api_tools.workflow import add_comment_to_workflow_run, get_workflow_run
from orcabus_api_tools.metadata import get_library_from_library_id
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
ANALYSIS_MIDFIX = "analysis"
LOGS_MIDFIX = "logs"
# Clinical workflow name
CLINICAL_WORKFLOW_NAME = 'clinical'

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
) -> Tuple[bool, str]:
    """
    Validate the engine parameters.
    :param engine_parameters: The engine parameters to validate.
    :param workflow_run_id: The workflow run ID
    :param project_prefix: The project prefix
    :return: A tuple of (is_valid, comment)
    """
    # Get the project id
    project_id = cast(str, engine_parameters.get("projectId"))

    # Confirm that the outputUri and logsUri are a subset of the project prefix
    output_uri = engine_parameters.get("outputUri", "")
    logs_uri = engine_parameters.get("logsUri", "")
    pipeline_id = engine_parameters.get("pipelineId", "")

    # Assert project id
    if project_id is None:
        return False, f"projectId is not set"
    try:
        get_project_obj_from_project_id(project_id)
    except ApiException:
        return False, f"Cannot find project id {project_id}"

    # Validate the uris are correct
    if not output_uri.startswith(project_prefix):
        return False, f"outputUri '{output_uri}' is not in the project context '{project_prefix}'"
    if not logs_uri.startswith(project_prefix):
        return False, f"logsUri '{logs_uri}' is not in the project context '{project_prefix}'"

    # Confirm the pipeline is in the project
    try:
        _ = get_project_pipeline_obj(
            project_id=project_id,
            pipeline_id=pipeline_id,
        )
    except ValueError as e:
        return False, f"The pipeline {pipeline_id} cannot be found in the project {project_id}"

    # Get the portal run id from the workflow run id
    portal_run_id = get_workflow_run(workflow_run_id)['portalRunId']

    # Confirm that the output uri, logs uri end with the portal run id
    if not output_uri.endswith(f"/{ANALYSIS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}/"):
        return False, f"outputUri '{output_uri}' does not end with '/{ANALYSIS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}'"
    if not logs_uri.endswith(f"/{LOGS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}/"):
        return False, f"logsUri '{logs_uri}' does not end with the portal run id '/{LOGS_MIDFIX}/{WORKFLOW_NAME}/{portal_run_id}'"

    return True, ""


def validate_inputs(
        inputs: Dict,
        project_id: str,
        project_prefix: str,
) -> Tuple[bool, str]:
    """
    Validate the inputs.

    :param inputs: The inputs to validate.
    :param project_id: The ICAv2 project id to validate against.
    :param project_prefix: The ICAv2 project prefix
    """
    # Get all fastq uris from the inputs
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

    # Remove empty values from list
    # Or externally mounted data uris (e.g. s3://reference-data-bucket/...)
    data_uris = list(filter(
        lambda uri_iter_: (
                uri_iter_ is not None and not (
                uri_iter_.startswith(f"s3://{REF_DATA_BUCKET}/") or
                uri_iter_.startswith(f"s3://{TEST_BUCKET}/") or
                uri_iter_.startswith(project_prefix)
        )
        ),
        data_uris
    ))

    # Validate each fastq uri
    for data_uri in data_uris:
        # Try get the icav2 object by uri
        try:
            project_data_obj = coerce_data_id_or_uri_to_project_data_obj(
                data_id_or_uri=data_uri,
            )
        except ValueError as e:
            return False, f"Data uri '{data_uri}' cannot be found in the project context '{project_id}'"

        # Then try get it in this context
        try:
            get_project_data_obj_by_id(
                project_id=project_id,
                data_id=project_data_obj.data.id
            )
        except ApiException as e:
            return False, f"Data uri '{data_uri}' cannot be found in the project context '{project_id}'"

    return True, ""


def validate_clinical_input_metrics(tags: PreLaunchSomaticTags) -> Tuple[bool, List[str]]:
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
    if not tags['ntsmInternalPassing']:
        is_valid = False
        comments.append("Normal internal fingerprint failed")
    if not tags['tumorNtsmInternalPassing']:
        is_valid = False
        comments.append("Tumor internal fingerprint failed")
    # 2. Cross fingerprint checks
    if not tags['ntsmExternalPassing']:
        is_valid = False
        comments.append("Fingerprints between tumor & normal did not match")

    # 3. Germline coverage checks
    if not tags['preLaunchCoverageEst'] >= MIN_RAW_NORMAL_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Normal did not meet raw threshold coverage of {MIN_RAW_NORMAL_WGS_COVERAGE} X")
    if (tags['preLaunchCoverageEst'] * (1 - tags['preLaunchDupFracEst'])) < MIN_DEDUP_NORMAL_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Normal deduplicated coverage estimate did not meet {MIN_DEDUP_NORMAL_WGS_COVERAGE} X")
    # 4. Somatic coverage checks
    if not tags['tumorPreLaunchCoverageEst'] >= MIN_RAW_TUMOR_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Tumor did not meet raw threshold coverage of {MIN_RAW_TUMOR_WGS_COVERAGE} X")
    if (tags['tumorPreLaunchCoverageEst'] * (1 - tags['tumorPreLaunchDupFracEst'])) < MIN_DEDUP_TUMOR_WGS_COVERAGE:
        is_valid = False
        comments.append(f"Tumor deduplicated coverage estimate did not meet {MIN_DEDUP_TUMOR_WGS_COVERAGE} X")

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

    # Get the ICAv2 project id from the event
    engine_parameters = payload_data.get("engineParameters", {})
    tags = payload_data.get("tags", {})

    # Get the project prefix
    project_prefix = cast(str, get_s3_key_prefix_by_project_id(engine_parameters.get("projectId")))

    # Confirm the engine parameters match
    is_valid, comment = validate_engine_parameters(
        engine_parameters,
        workflow_run_id=workflow_run_id,
        project_prefix=project_prefix,
    )

    # Check if the inputs are also valid
    if is_valid:
        # Get the inputs and confirm that the fastq uris are valid
        # and are accessible in the right project context
        inputs = payload_data.get("inputs")
        # Validate the inputs
        is_valid, comment = validate_inputs(
            inputs,
            project_id=engine_parameters.get("projectId"),
            # Get the key prefix for the project
            project_prefix=cast(str, get_s3_key_prefix_by_project_id(engine_parameters.get("projectId")))
        )

    # Check if this is a clinical sample and if we
    # Need to hold off until coverage matches
    if is_valid:
        tumor_library_id = tags.get("tumorLibraryId", None)
        # Germline only run
        if tumor_library_id is None:
            pass
        # Not a clinical sample
        elif not get_library_from_library_id(tumor_library_id)['workflow'] == CLINICAL_WORKFLOW_NAME:
            pass
        # Clinical TN Sample
        else:
            is_valid, comment = validate_clinical_input_metrics(
                tags
            )

    # Somewhere along the way, the validation failed
    if not is_valid:
        if isinstance(comment, list) and len(comment) == 1:
            comment = comment[0]
        if isinstance(comment, list):
                workflow_run_orcabus_id=workflow_run_id,
                comment=f"Post schema validation failed for {len(comment)} reasons",
                author=COMMENT_AUTHOR
            )
            for idx, comment_iter in enumerate(comment):
                add_comment_to_workflow_run(
                    workflow_run_orcabus_id=workflow_run_id,
                    comment=f"Reason {idx}: {comment_iter}",
                    author=COMMENT_AUTHOR
                )
                sleep(1)
        else:
            add_comment_to_workflow_run(
                workflow_run_orcabus_id=workflow_run_id,
                comment=f"Post schema validation failed: {comment}",
                author=COMMENT_AUTHOR
            )
        return {
            "isValid": False
        }

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
            comment=comment,
            author=COMMENT_AUTHOR
        )

    return {
        "isValid": True
    }
