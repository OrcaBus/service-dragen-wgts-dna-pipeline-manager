---
inclusion: fileMatch
fileMatchPattern: '**/*post_schema_validation*'
---

# Post-Schema Validation Standards

Standards for the `post_schema_validation` Lambda that performs business-rule checks after JSON Schema validation passes. This Lambda is invoked in the `validateDraftDataAndPutReadyEvent` state machine.

## Lambda Name

The Lambda must be named `post_schema_validation` (directory: `post_schema_validation_py/`). It is triggered from the validate-draft-and-put-ready-event step function after the JSON schema check passes.

## Engine Parameter Checks

The following checks must be performed on `data.engineParameters`:

### Project Context Validation

- Confirm `projectId` is set and resolves to a valid ICAv2 project
- Confirm `outputUri` starts with the project's S3 key prefix (i.e. is within the project context)
- Confirm `logsUri` starts with the project's S3 key prefix

### URI Structure Validation

- `outputUri` must end with `/<analysis-midfix>/<workflow-name>/<portal-run-id>/`
  - The analysis midfix is one of: `analysis`, `output`, `outputs` (prefer `analysis`)
- `logsUri` must end with `/logs/<workflow-name>/<portal-run-id>/`
- Confirm the `pipelineId` is accessible in the specified `projectId`

### Cache URI (if applicable)

- If the pipeline uses a cache URI, confirm it is also within the project prefix

## Input Checks

For workflow runs in an ICA context, validate all data URIs in the inputs:

### URI Location Rules

For any URI input (FASTQ files, reference tarballs, ORA references):

1. **Allowed without further checks**:
   - URIs in the **reference data bucket** (`s3://<ref-data-bucket>/...`)
   - URIs in the **test data bucket** (`s3://<test-data-bucket>/...`)
   - URIs already under the **project prefix** (within the project's S3 context)

2. **Requires ICA validation**:
   - Any URI that does NOT meet the above criteria must be checked via `wrapica.project_data.coerce_data_id_or_uri_to_project_data_obj` to confirm the data has been linked to the project via an ICA call
   - If the data cannot be found in the project context, fail validation with a descriptive comment

### Implementation Pattern

```python
from wrapica.project_data import coerce_data_id_or_uri_to_project_data_obj, get_project_data_obj_by_id
from wrapica.storage_configuration import get_s3_key_prefix_by_project_id

# Get project prefix
project_prefix = get_s3_key_prefix_by_project_id(project_id)

# Filter URIs that need validation (not in ref/test/project-prefix)
uris_to_validate = [
    uri for uri in all_data_uris
    if not (
        uri.startswith(f"s3://{REF_DATA_BUCKET}/") or
        uri.startswith(f"s3://{TEST_BUCKET}/") or
        uri.startswith(project_prefix)
    )
]

# Validate each URI is accessible in the project
for uri in uris_to_validate:
    data_obj = coerce_data_id_or_uri_to_project_data_obj(data_id_or_uri=uri)
    get_project_data_obj_by_id(project_id=project_id, data_id=data_obj.data.id)
```

## Failure Handling

- On validation failure, write a descriptive comment to the workflow run record using `add_comment_to_workflow_run`
- Return `{"isValid": False}` — the step function will exit silently without emitting a READY event
- If multiple failures, write each as a separate numbered comment
- On success with notes (e.g. downsampling enabled), write informational comments and return `{"isValid": True}`

## Pipeline-Specific Extensions

Individual pipelines may add additional checks beyond the above (e.g. coverage thresholds, fingerprint concordance for clinical samples). These are service-specific and not part of this shared standard.
