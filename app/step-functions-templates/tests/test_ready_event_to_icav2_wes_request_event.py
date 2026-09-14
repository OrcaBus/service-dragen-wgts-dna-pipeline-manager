"""TestState API tests for ready_event_to_icav2_wes_request_event_sfn_template.

Validates JSONata expressions and Task state data flow for the state machine
that converts a READY event into an ICAv2 WES request event.
"""

from __future__ import annotations

import json

import boto3
import pytest

from orcabus_pipeline_test_utils.sfn_teststate import TestStateClient, TestStateAssertion

TEMPLATE_NAME = "ready_event_to_icav2_wes_request_event_sfn_template"

# Capture SFN client at import time before moto overwrites credentials.
_SFN_CLIENT = boto3.client("stepfunctions", region_name="ap-southeast-2")


@pytest.fixture(scope="module")
def sfn_client():
    """TestState client with real AWS credentials."""
    return TestStateClient(region_name="ap-southeast-2", client=_SFN_CLIENT)


@pytest.mark.sfn_teststate
class TestSaveInputs:
    """Test the initial 'Save inputs' Pass state."""

    def test_assigns_input_as_variable(self, sfn_client, load_template):
        """Pass state should assign the full input as dragenWgtsDnaReadyEventDetail."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={
                "portalRunId": "20250606test",
                "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606test",
                "payload": {"data": {"inputs": {}, "engineParameters": {}, "tags": {}}},
            },
            state_name="Save inputs",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Add Ready Comment").passed


@pytest.mark.sfn_teststate
class TestAddReadyComment:
    """Test the 'Add Ready Comment' Task state."""

    def test_succeeds_with_mocked_lambda(self, sfn_client, load_template):
        """Should invoke Lambda and route to conversion step."""
        definition = load_template(TEMPLATE_NAME)

        result = sfn_client.test_state(
            definition=definition,
            input_data={},
            variables={
                "dragenWgtsDnaReadyEventDetail": {
                    "orcabusId": "wfr.TEST123",
                    "portalRunId": "20250606test",
                    "workflowRunName": "umccr--automated--dragen-wgts-dna--4-4-4--20250606test",
                    "payload": {"data": {"inputs": {}, "engineParameters": {}, "tags": {}}},
                },
            },
            state_name="Add Ready Comment",
            mock_result={"Payload": {}, "StatusCode": 200},
            field_validation_mode="NONE",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state(
            "Convert Dragen WGTS DNA Ready Event to ICAv2 WES Event"
        ).passed
