"""Tests for post_schema_validation Lambda function.

This Lambda performs post-schema validation: checking that input URIs exist and
are accessible in the correct ICAv2 project context, and validating clinical
sample coverage thresholds. It uses multiple external services (ICAv2, OrcaBus APIs,
Filemanager) which we mock here.
"""

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — mock all external layers before importing
# ---------------------------------------------------------------------------
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "post_schema_validation_py"

# Mock wrapica
_mock_wrapica = ModuleType("wrapica")
_mock_project_data = ModuleType("wrapica.project_data")
_mock_project_data.coerce_data_id_or_uri_to_project_data_obj = MagicMock()
_mock_project_data.get_project_data_obj_by_id = MagicMock()
_mock_storage_config = ModuleType("wrapica.storage_configuration")
_mock_storage_config.get_s3_key_prefix_by_project_id = MagicMock()
_mock_project_pipelines = ModuleType("wrapica.project_pipelines")
_mock_project_pipelines.get_project_pipeline_obj = MagicMock()
_mock_project = ModuleType("wrapica.project")
_mock_project.get_project_obj_from_project_id = MagicMock()
_mock_wrapica.project_data = _mock_project_data
_mock_wrapica.storage_configuration = _mock_storage_config
_mock_wrapica.project_pipelines = _mock_project_pipelines
_mock_wrapica.project = _mock_project

# Mock libica
_mock_libica = ModuleType("libica")
_mock_libica_openapi = ModuleType("libica.openapi")
_mock_libica_v3 = ModuleType("libica.openapi.v3")
_mock_libica_v3.ApiException = type("ApiException", (Exception,), {})
_mock_libica.openapi = _mock_libica_openapi
_mock_libica_openapi.v3 = _mock_libica_v3

# Mock icav2_tools
_mock_icav2_tools = ModuleType("icav2_tools")
_mock_icav2_tools.set_icav2_env_vars = MagicMock()

# Mock orcabus_api_tools
_mock_api_tools = ModuleType("orcabus_api_tools")
_mock_workflow = ModuleType("orcabus_api_tools.workflow")
_mock_workflow.add_comment_to_workflow_run = MagicMock()
_mock_workflow.get_workflow_run = MagicMock()
_mock_metadata = ModuleType("orcabus_api_tools.metadata")
_mock_metadata.get_library_from_library_id = MagicMock()
_mock_filemanager = ModuleType("orcabus_api_tools.filemanager")
_mock_filemanager.get_s3_object_id_from_s3_uri = MagicMock()
_mock_filemanager.list_files_recursively = MagicMock()
_mock_filemanager_errors = ModuleType("orcabus_api_tools.filemanager.errors")
_mock_filemanager_errors.S3FileNotFoundError = type("S3FileNotFoundError", (Exception,), {})
_mock_filemanager.errors = _mock_filemanager_errors
_mock_api_tools.workflow = _mock_workflow
_mock_api_tools.metadata = _mock_metadata
_mock_api_tools.filemanager = _mock_filemanager

sys.modules["wrapica"] = _mock_wrapica
sys.modules["wrapica.project_data"] = _mock_project_data
sys.modules["wrapica.storage_configuration"] = _mock_storage_config
sys.modules["wrapica.project_pipelines"] = _mock_project_pipelines
sys.modules["wrapica.project"] = _mock_project
sys.modules["libica"] = _mock_libica
sys.modules["libica.openapi"] = _mock_libica_openapi
sys.modules["libica.openapi.v3"] = _mock_libica_v3
sys.modules["icav2_tools"] = _mock_icav2_tools
sys.modules["orcabus_api_tools"] = _mock_api_tools
sys.modules["orcabus_api_tools.workflow"] = _mock_workflow
sys.modules["orcabus_api_tools.metadata"] = _mock_metadata
sys.modules["orcabus_api_tools.filemanager"] = _mock_filemanager
sys.modules["orcabus_api_tools.filemanager.errors"] = _mock_filemanager_errors

# Set env vars BEFORE importing (handler reads them at module level)
os.environ.setdefault("WORKFLOW_NAME", "dragen-wgts-dna")
os.environ.setdefault("TEST_DATA_BUCKET_NAME", "test-data-bucket")
os.environ.setdefault("REF_DATA_BUCKET_NAME", "ref-data-bucket")
os.environ.setdefault("MIN_RAW_TUMOR_WGS_COVERAGE", "60")
os.environ.setdefault("MIN_DEDUP_TUMOR_WGS_COVERAGE", "50")
os.environ.setdefault("MIN_RAW_NORMAL_WGS_COVERAGE", "30")
os.environ.setdefault("MIN_DEDUP_NORMAL_WGS_COVERAGE", "25")

sys.path.insert(0, str(LAMBDA_DIR))

from post_schema_validation import handler  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset all mocks between tests."""
    _mock_storage_config.get_s3_key_prefix_by_project_id.reset_mock()
    _mock_project.get_project_obj_from_project_id.reset_mock()
    _mock_project_pipelines.get_project_pipeline_obj.reset_mock()
    _mock_workflow.add_comment_to_workflow_run.reset_mock()
    _mock_workflow.get_workflow_run.reset_mock()
    _mock_filemanager.get_s3_object_id_from_s3_uri.reset_mock()
    _mock_filemanager.list_files_recursively.reset_mock()
    _mock_metadata.get_library_from_library_id.reset_mock()
    _mock_icav2_tools.set_icav2_env_vars.reset_mock()

    # Default mock return values
    _mock_storage_config.get_s3_key_prefix_by_project_id.return_value = (
        "s3://project-bucket/byob-icav2/project/"
    )
    _mock_project.get_project_obj_from_project_id.return_value = {"id": "proj-456"}
    _mock_project_pipelines.get_project_pipeline_obj.return_value = {"id": "pipe-123"}
    _mock_workflow.get_workflow_run.return_value = {
        "portalRunId": "20250606abcd1234",  # pragma: allowlist secret
        "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606abcd1234",
    }
    _mock_filemanager.get_s3_object_id_from_s3_uri.return_value = {"s3ObjectId": "obj-123"}
    yield


def _make_valid_event():
    """Build a minimal valid event for post_schema_validation."""
    return {
        "workflowRunId": "wfr.abc123",
        "executionArn": "arn:aws:states:ap-southeast-2:123456:execution:sfn:exec-1",
        "data": {
            "inputs": {
                "sampleName": "L2301197",
                "reference": {"name": "hg38", "structure": "linear", "tarball": "s3://ref-data-bucket/hg38.tar.gz"},
                "sequenceData": {
                    "fastqListRows": [
                        {"rgid": "RG1", "read1FileUri": "s3://project-bucket/byob-icav2/project/r1.fq", "read2FileUri": "s3://project-bucket/byob-icav2/project/r2.fq"}
                    ]
                },
            },
            "engineParameters": {
                "projectId": "proj-456",
                "pipelineId": "pipe-123",
                "outputUri": "s3://project-bucket/byob-icav2/project/analysis/dragen-wgts-dna/20250606abcd1234/",
                "logsUri": "s3://project-bucket/byob-icav2/project/logs/dragen-wgts-dna/20250606abcd1234/",
            },
            "tags": {"libraryId": "L2301197"},
        },
    }


@pytest.mark.lambda_unit
class TestPostSchemaValidationValid:
    """Test cases where the post-schema validation passes."""

    def test_valid_germline_event(self, event_builder, lambda_context):
        """A valid germline event should return isValid=True."""
        event = event_builder(_make_valid_event())

        result = handler(event, lambda_context())

        assert result == {"isValid": True}

    def test_sets_icav2_env_vars(self, event_builder, lambda_context):
        """Should call set_icav2_env_vars."""
        event = event_builder(_make_valid_event())

        handler(event, lambda_context())

        _mock_icav2_tools.set_icav2_env_vars.assert_called_once()


@pytest.mark.lambda_unit
class TestPostSchemaValidationEngineParameterErrors:
    """Test engine parameter validation failures."""

    def test_invalid_output_uri_prefix(self, event_builder, lambda_context):
        """OutputUri not in project prefix should fail validation."""
        event_data = _make_valid_event()
        event_data["data"]["engineParameters"]["outputUri"] = (
            "s3://wrong-bucket/analysis/dragen-wgts-dna/20250606abcd1234/"
        )
        event = event_builder(event_data)

        result = handler(event, lambda_context())

        assert result == {"isValid": False}
        _mock_workflow.add_comment_to_workflow_run.assert_called()

    def test_invalid_logs_uri_prefix(self, event_builder, lambda_context):
        """LogsUri not in project prefix should fail validation."""
        event_data = _make_valid_event()
        event_data["data"]["engineParameters"]["logsUri"] = (
            "s3://wrong-bucket/logs/dragen-wgts-dna/20250606abcd1234/"
        )
        event = event_builder(event_data)

        result = handler(event, lambda_context())

        assert result == {"isValid": False}
