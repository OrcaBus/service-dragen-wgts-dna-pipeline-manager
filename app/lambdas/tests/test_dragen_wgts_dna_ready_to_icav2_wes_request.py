"""Tests for dragen_wgts_dna_ready_to_icav2_wes_request Lambda function.

This Lambda converts a DRAGEN WGTS DNA READY event detail into an ICAv2 WES
request event. It performs pure data transformations:
- Converts camelCase input keys to snake_case
- Converts file URIs to CWL File/Directory objects
- Restructures the event into ICAv2 WES request format
"""

import sys
from pathlib import Path

import pytest

# Path setup for Lambda handler import
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "dragen_wgts_dna_ready_to_icav2_wes_request_py"
sys.path.insert(0, str(LAMBDA_DIR))

from dragen_wgts_dna_ready_to_icav2_wes_request import handler  # noqa: E402


def _make_ready_event(
    *,
    portal_run_id="20250606efgh1234",
    workflow_run_name="umccr--automated--dragen-wgts-dna--4-4-4--20250606efgh1234",
    inputs=None,
    engine_parameters=None,
    tags=None,
):
    """Helper to build a minimal READY event detail."""
    if inputs is None:
        inputs = {
            "sampleName": "L2301197",
            "reference": {
                "name": "hg38",
                "structure": "graph",
                "tarball": "s3://bucket/reference.tar.gz",
            },
            "sequenceData": {
                "fastqListRows": [
                    {
                        "rgid": "RG001",
                        "rglb": "L2301197",
                        "rgsm": "L2301197",
                        "lane": 1,
                        "read1FileUri": "s3://bucket/R1.fastq.ora",
                        "read2FileUri": "s3://bucket/R2.fastq.ora",
                    }
                ]
            },
        }
    if engine_parameters is None:
        engine_parameters = {
            "pipelineId": "pipeline-123",
            "projectId": "proj-456",
            "outputUri": "s3://bucket/output/",
            "logsUri": "s3://bucket/logs/",
        }
    if tags is None:
        tags = {"libraryId": "L2301197"}

    return {
        "dragenWgtsDnaReadyEventDetail": {
            "portalRunId": portal_run_id,
            "timestamp": "2025-06-06T04:39:31+00:00",
            "status": "READY",
            "workflowName": "dragen-wgts-dna",
            "workflowVersion": "4.4.4",
            "workflowRunName": workflow_run_name,
            "linkedLibraries": [{"libraryId": "L2301197", "orcabusId": "lib.ABC123"}],
            "payload": {
                "refId": "ref-uuid",
                "version": "2025.06.06",
                "data": {
                    "inputs": inputs,
                    "engineParameters": engine_parameters,
                    "tags": tags,
                },
            },
        }
    }


@pytest.mark.lambda_unit
class TestReadyToWesRequestHappyPath:
    """Test the happy-path conversion from READY event to ICAv2 WES request."""

    def test_output_structure(self, lambda_context):
        """Output should contain icav2WesRequestEventDetail with name, inputs, engineParameters, tags."""
        event = _make_ready_event()
        result = handler(event, lambda_context())

        assert "icav2WesRequestEventDetail" in result
        detail = result["icav2WesRequestEventDetail"]
        assert "name" in detail
        assert "inputs" in detail
        assert "engineParameters" in detail
        assert "tags" in detail

    def test_workflow_run_name_preserved(self, lambda_context):
        """The workflow run name should be passed through as 'name'."""
        event = _make_ready_event(
            workflow_run_name="umccr--automated--dragen-wgts-dna--4-4-4--20250606test1234"
        )
        result = handler(event, lambda_context())

        assert result["icav2WesRequestEventDetail"]["name"] == (
            "umccr--automated--dragen-wgts-dna--4-4-4--20250606test1234"
        )

    def test_portal_run_id_added_to_tags(self, lambda_context):
        """The portalRunId should be added to the tags."""
        event = _make_ready_event(portal_run_id="20250101abcd5678")
        result = handler(event, lambda_context())

        tags = result["icav2WesRequestEventDetail"]["tags"]
        assert tags["portalRunId"] == "20250101abcd5678"  # pragma: allowlist secret

    def test_original_tags_preserved(self, lambda_context):
        """Original tags from the READY event should be preserved."""
        event = _make_ready_event(tags={"libraryId": "L999", "subjectId": "SBJ001"})
        result = handler(event, lambda_context())

        tags = result["icav2WesRequestEventDetail"]["tags"]
        assert tags["libraryId"] == "L999"
        assert tags["subjectId"] == "SBJ001"

    def test_engine_parameters_passed_through(self, lambda_context):
        """Engine parameters should be passed through unchanged."""
        engine_params = {
            "pipelineId": "pipe-abc",
            "projectId": "proj-xyz",
            "outputUri": "s3://out/",
            "logsUri": "s3://logs/",
        }
        event = _make_ready_event(engine_parameters=engine_params)
        result = handler(event, lambda_context())

        assert result["icav2WesRequestEventDetail"]["engineParameters"] == engine_params


@pytest.mark.lambda_unit
class TestCamelToSnakeCaseConversion:
    """Test that input keys are converted from camelCase to snake_case."""

    def test_top_level_keys_converted(self, lambda_context):
        """Top-level input keys should be snake_case."""
        event = _make_ready_event()
        result = handler(event, lambda_context())

        inputs = result["icav2WesRequestEventDetail"]["inputs"]
        assert "sample_name" in inputs
        assert "sampleName" not in inputs

    def test_nested_keys_converted(self, lambda_context):
        """Nested keys should also be snake_case."""
        inputs = {
            "sampleName": "SMP001",
            "reference": {"name": "hg38", "structure": "graph", "tarball": "s3://ref.tar.gz"},
            "alignmentOptions": {"enableDuplicateMarking": True},
            "sequenceData": {
                "fastqListRows": [
                    {"rgid": "RG1", "rglb": "L1", "rgsm": "S1", "lane": 1,
                     "read1FileUri": "s3://r1.fq", "read2FileUri": "s3://r2.fq"}
                ]
            },
        }
        event = _make_ready_event(inputs=inputs)
        result = handler(event, lambda_context())

        converted = result["icav2WesRequestEventDetail"]["inputs"]
        assert "alignment_options" in converted
        assert "enable_duplicate_marking" in converted["alignment_options"]


@pytest.mark.lambda_unit
class TestCwlFileConversion:
    """Test that file URIs are converted to CWL File objects."""

    def test_reference_tarball_converted(self, lambda_context):
        """Reference tarball URI should become a CWL File object."""
        event = _make_ready_event()
        result = handler(event, lambda_context())

        ref = result["icav2WesRequestEventDetail"]["inputs"]["reference"]
        assert ref["tarball"] == {"class": "File", "location": "s3://bucket/reference.tar.gz"}

    def test_fastq_read_uris_converted(self, lambda_context):
        """read1FileUri and read2FileUri should become read_1/read_2 CWL File objects."""
        event = _make_ready_event()
        result = handler(event, lambda_context())

        rows = result["icav2WesRequestEventDetail"]["inputs"]["sequence_data"]["fastq_list_rows"]
        assert len(rows) == 1
        assert rows[0]["read_1"] == {"class": "File", "location": "s3://bucket/R1.fastq.ora"}
        assert rows[0]["read_2"] == {"class": "File", "location": "s3://bucket/R2.fastq.ora"}

    def test_ora_reference_converted(self, lambda_context):
        """oraReference URI should become a CWL File object."""
        inputs = {
            "sampleName": "SMP001",
            "reference": {"name": "hg38", "structure": "graph", "tarball": "s3://ref.tar.gz"},
            "oraReference": "s3://bucket/ora_ref.tar.gz",
            "sequenceData": {
                "fastqListRows": [
                    {"rgid": "RG1", "rglb": "L1", "rgsm": "S1", "lane": 1,
                     "read1FileUri": "s3://r1.fq", "read2FileUri": "s3://r2.fq"}
                ]
            },
        }
        event = _make_ready_event(inputs=inputs)
        result = handler(event, lambda_context())

        converted = result["icav2WesRequestEventDetail"]["inputs"]
        assert converted["ora_reference"] == {"class": "File", "location": "s3://bucket/ora_ref.tar.gz"}

    def test_somatic_reference_tarball_converted(self, lambda_context):
        """somaticReference.tarball should become a CWL File object."""
        inputs = {
            "sampleName": "SMP001",
            "reference": {"name": "hg38", "structure": "graph", "tarball": "s3://ref.tar.gz"},
            "somaticReference": {"name": "hg38", "structure": "graph", "tarball": "s3://somatic_ref.tar.gz"},
            "sequenceData": {
                "fastqListRows": [
                    {"rgid": "RG1", "rglb": "L1", "rgsm": "S1", "lane": 1,
                     "read1FileUri": "s3://r1.fq", "read2FileUri": "s3://r2.fq"}
                ]
            },
        }
        event = _make_ready_event(inputs=inputs)
        result = handler(event, lambda_context())

        converted = result["icav2WesRequestEventDetail"]["inputs"]
        assert converted["somatic_reference"]["tarball"] == {
            "class": "File",
            "location": "s3://somatic_ref.tar.gz",
        }


@pytest.mark.lambda_unit
class TestTumorNormalInputs:
    """Test tumor/normal paired inputs."""

    def test_tumor_fastq_list_rows_converted(self, lambda_context):
        """tumorSequenceData.fastqListRows should also get CWL File conversion."""
        inputs = {
            "sampleName": "NORMAL001",
            "tumorSampleName": "TUMOR001",
            "reference": {"name": "hg38", "structure": "graph", "tarball": "s3://ref.tar.gz"},
            "sequenceData": {
                "fastqListRows": [
                    {"rgid": "RG_N", "rglb": "LN", "rgsm": "SN", "lane": 1,
                     "read1FileUri": "s3://normal_r1.fq", "read2FileUri": "s3://normal_r2.fq"}
                ]
            },
            "tumorSequenceData": {
                "fastqListRows": [
                    {"rgid": "RG_T", "rglb": "LT", "rgsm": "ST", "lane": 1,
                     "read1FileUri": "s3://tumor_r1.fq", "read2FileUri": "s3://tumor_r2.fq"}
                ]
            },
        }
        event = _make_ready_event(inputs=inputs)
        result = handler(event, lambda_context())

        converted = result["icav2WesRequestEventDetail"]["inputs"]
        tumor_rows = converted["tumor_sequence_data"]["fastq_list_rows"]
        assert tumor_rows[0]["read_1"] == {"class": "File", "location": "s3://tumor_r1.fq"}
        assert tumor_rows[0]["read_2"] == {"class": "File", "location": "s3://tumor_r2.fq"}
