"""TestState API tests for validate_draft_data_and_put_ready_event_sfn_template.

Validates JSONata expressions, Choice branching, and Task state data flow
for the validation + READY event emission state machine.
"""

from __future__ import annotations

import json

import boto3
import pytest

from orcabus_pipeline_test_utils.sfn_teststate import TestStateClient, TestStateAssertion

TEMPLATE_NAME = "validate_draft_data_and_put_ready_event_sfn_template"

# Capture SFN client at import time before moto overwrites credentials.
_SFN_CLIENT = boto3.client("stepfunctions", region_name="ap-southeast-2")


@pytest.fixture(scope="module")
def sfn_client():
    """TestState client with real AWS credentials."""
    return TestStateClient(region_name="ap-southeast-2", client=_SFN_CLIENT)


@pytest.mark.sfn_teststate
class TestSaveEventVars:
    """Test the initial Pass state variable assignment."""

    def test_assigns_variables_from_input(self, sfn_client, load_template, load_scenario):
        """Pass state should assign detail, workflowRunId, payload, payloadData."""
        definition = load_template(TEMPLATE_NAME)
        scenario = load_scenario(TEMPLATE_NAME, "happy_path")

        result = sfn_client.test_state(
            definition=definition,
            input_data=scenario["input"],
            state_name="Save Event Vars",
            inspection_level="DEBUG",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Validate Draft Complete Event").passed


@pytest.mark.sfn_teststate
class TestIsDraftEventComplete:
    """Test the 'Is Draft Event Complete?' Choice state branching."""

    def test_valid_routes_to_post_schema_validation(self, sfn_client, load_template):
        """When isValid=true, should route to 'Run post-schema validation'."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": True},
            state_name="Is Draft Event Complete?",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Run post-schema validation").passed

    def test_invalid_routes_to_pass(self, sfn_client, load_template):
        """When isValid=false, should exit via 'Pass' without emitting READY."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": False},
            state_name="Is Draft Event Complete?",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Pass").passed


@pytest.mark.sfn_teststate
class TestValidateDraftCompleteEvent:
    """Test the validation Task state with mocked Lambda responses."""

    def test_valid_schema_extracts_is_valid_true(self, sfn_client, load_template):
        """Should extract isValid=true from mocked Lambda Payload."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={},
            variables={
                "payloadData": {"inputs": {}, "engineParameters": {}},
                "workflowRunId": "wfr.ABCDEF123456",
            },
            state_name="Validate Draft Complete Event",
            mock_result={"Payload": {"isValid": True}, "StatusCode": 200},
            field_validation_mode="NONE",
            inspection_level="DEBUG",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Is Draft Event Complete?").passed
        assert assertion.assert_output({"isValid": True}).passed

    def test_invalid_schema_extracts_is_valid_false(self, sfn_client, load_template):
        """Should extract isValid=false from mocked Lambda Payload."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={},
            variables={
                "payloadData": {},
                "workflowRunId": "wfr.ABCDEF123456",
            },
            state_name="Validate Draft Complete Event",
            mock_result={"Payload": {"isValid": False}, "StatusCode": 200},
            field_validation_mode="NONE",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_output({"isValid": False}).passed


@pytest.mark.sfn_teststate
class TestWorkflowInputsAreValid:
    """Test the 'Workflow Inputs are Valid' Choice state."""

    def test_valid_inputs_route_to_push_ready_event(self, sfn_client, load_template):
        """When isValid=true, should route to 'Push READY Event'."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": True},
            state_name="Workflow Inputs are Valid",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Push READY Event").passed

    def test_invalid_inputs_route_to_pass(self, sfn_client, load_template):
        """When isValid=false, should exit via 'Pass'."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": False},
            state_name="Workflow Inputs are Valid",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Pass").passed
