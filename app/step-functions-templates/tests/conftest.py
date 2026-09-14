"""Step Functions test fixtures for service-dragen-wgts-dna-pipeline-manager.

Provides fixtures for loading ASL templates, scenarios, mock configurations,
and TestState API client access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orcabus_pipeline_test_utils.asl_validation.placeholder_resolver import (
    resolve_placeholders,
)
from orcabus_pipeline_test_utils.sfn_teststate import (
    TestStateClient,
    TestStateAssertion,
    PathAssertion,
)


# Directory paths
TEMPLATES_DIR = Path(__file__).parent.parent
TESTS_DIR = Path(__file__).parent
MOCKS_DIR = TESTS_DIR / "mocks"
SCENARIOS_DIR = TESTS_DIR / "scenarios"

# SFN template names (without .asl.json suffix)
SFN_TEMPLATES = [
    "populate_draft_data_sfn_template",
    "validate_draft_data_and_put_ready_event_sfn_template",
    "ready_event_to_icav2_wes_request_event_sfn_template",
    "icav2_wes_event_to_wrsc_event_sfn_template",
]


@pytest.fixture
def load_template():
    """Factory fixture to load and return an ASL template as a dict.

    Automatically resolves ${__placeholder__} references with dummy ARNs.
    """

    def _load(template_name: str) -> dict:
        template_path = TEMPLATES_DIR / f"{template_name}.asl.json"
        raw_content = template_path.read_text()
        resolved_content = resolve_placeholders(raw_content)
        return json.loads(resolved_content)

    return _load


@pytest.fixture
def load_scenario():
    """Factory fixture to load a scenario JSON file.

    Usage:
        scenario = load_scenario("populate_draft_data_sfn_template", "happy_path")
    """

    def _load(template_name: str, scenario_name: str) -> dict:
        scenario_path = SCENARIOS_DIR / template_name / f"{scenario_name}.json"
        return json.loads(scenario_path.read_text())

    return _load


@pytest.fixture
def load_mock_config():
    """Factory fixture to load a MockConfigFile.json for a given template.

    Usage:
        mock_config = load_mock_config("populate_draft_data_sfn_template")
    """

    def _load(template_name: str) -> dict:
        mock_config_path = MOCKS_DIR / template_name / "MockConfigFile.json"
        return json.loads(mock_config_path.read_text())

    return _load


@pytest.fixture
def teststate_client():
    """Provide a TestState API client for state-level testing.

    Returns a TestStateClient configured for the ap-southeast-2 region.
    Requires AWS credentials with states:TestState permission.

    Note: This fixture creates a fresh boto3 session that reads credentials
    from the environment/config files directly, bypassing the moto-based
    mock credentials set by the plugin's _aws_credentials fixture.
    When a mock parameter is provided to test_state(), no roleArn is required.
    """
    import os
    import boto3

    # Create a session that bypasses the moto dummy credentials
    # by reading from the default credential chain (env vars, config files, instance profile)
    session = boto3.Session(region_name="ap-southeast-2")
    return TestStateClient(region_name="ap-southeast-2", session=session)
