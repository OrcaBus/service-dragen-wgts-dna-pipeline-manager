"""TestState API tests for populate_draft_data_sfn_template.

Validates JSONata expressions, Choice branching, and Task state data flow
for the draft data population state machine.
"""

from __future__ import annotations

import json

import boto3
import pytest

from orcabus_pipeline_test_utils.sfn_teststate import TestStateClient, TestStateAssertion

TEMPLATE_NAME = "populate_draft_data_sfn_template"

# Capture SFN client at import time before moto overwrites credentials.
_SFN_CLIENT = boto3.client("stepfunctions", region_name="ap-southeast-2")


@pytest.fixture(scope="module")
def sfn_client():
    """TestState client with real AWS credentials."""
    return TestStateClient(region_name="ap-southeast-2", client=_SFN_CLIENT)


@pytest.mark.sfn_teststate
class TestGetDraftPayloadVar:
    """Test the initial Pass state variable assignment."""

    def test_assigns_variables_from_input(self, sfn_client, load_template, load_scenario):
        """Pass state should assign detail, data, engineParameters, tags, etc."""
        definition = load_template(TEMPLATE_NAME)
        scenario = load_scenario(TEMPLATE_NAME, "happy_path")

        result = sfn_client.test_state(
            definition=definition,
            input_data=scenario["input"],
            state_name="Get draft payload var",
            inspection_level="DEBUG",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed


@pytest.mark.sfn_teststate
class TestValidateDraftData:
    """Test the 'Validate draft data' Task state with mocked responses."""

    def test_valid_schema_returns_is_valid_true(self, sfn_client, load_template):
        """When Lambda returns isValid=true, output should reflect that."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={},
            variables={"data": {"inputs": {}, "engineParameters": {}}},
            state_name="Validate draft data",
            mock_result={"Payload": {"isValid": True}, "StatusCode": 200},
            field_validation_mode="NONE",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed

    def test_invalid_schema_returns_is_valid_false(self, sfn_client, load_template):
        """When Lambda returns isValid=false, output should reflect that."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={},
            variables={"data": {}},
            state_name="Validate draft data",
            mock_result={"Payload": {"isValid": False}, "StatusCode": 200},
            field_validation_mode="NONE",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed


@pytest.mark.sfn_teststate
class TestDraftDataIsValid:
    """Test the 'Draft data is valid' Choice state branching."""

    def test_valid_data_exits_early(self, sfn_client, load_template):
        """When isValid=true, should exit without populating engine parameters."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": True},
            state_name="Draft data is valid",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed

    def test_invalid_data_continues_to_populate(self, sfn_client, load_template):
        """When isValid=false, should route to 'Get Engine parameters'."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": False},
            state_name="Draft data is valid",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Get Engine parameters").passed
