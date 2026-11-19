# Python App Tests

Shared test dependencies, configuration, and documentation for all Python tests in this service.

## Directory Layout

```
app/
├── tests/
│   └── requirements-test.txt                # Shared Python test dependencies
├── lambdas/
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                      # Service-specific fixtures + shared plugin registration
│       ├── test_*.py                        # One test file per Lambda function
│       └── examples/                        # Example test templates for common patterns
│           ├── test_data_transformation_example.py
│           ├── test_api_call_example.py
│           └── test_validation_example.py
└── step-functions-templates/
    └── tests/
        ├── __init__.py
        ├── conftest.py                      # SFN fixtures (TestState client, template loader, scenarios)
        ├── test_asl_validation.py           # ASL structural validation tests
        ├── test_teststate_integration.py    # TestState API integration tests (sfn_teststate marker)
        ├── test_*.py                        # One test file per Step Function template
        ├── mocks/                           # MockConfigFile.json per state machine
        │   ├── populate_draft_data_sfn_template/
        │   ├── validate_draft_data_and_put_ready_event_sfn_template/
        │   ├── ready_event_to_icav2_wes_request_event_sfn_template/
        │   └── icav2_wes_event_to_wrsc_event_sfn_template/
        └── scenarios/                       # Input/output scenario definitions per SFN
            ├── populate_draft_data_sfn_template/
            ├── validate_draft_data_and_put_ready_event_sfn_template/
            ├── ready_event_to_icav2_wes_request_event_sfn_template/
            └── icav2_wes_event_to_wrsc_event_sfn_template/
```

## Prerequisites

- Python 3.14+

## Install Dependencies

```bash
pip install -r app/tests/requirements-test.txt
```

This installs:

- `orcabus-pipeline-test-utils` — shared pytest plugin (fixtures + ASL validation + TestState API harness)
- `pytest` — test runner
- `moto` — AWS service mocking (S3, SSM, Secrets Manager, EventBridge, Lambda)
- `boto3` — AWS SDK
- `jsonschema` — JSON schema validation
- `deepdiff` — deep payload comparison (used by `compare_payload` Lambda)

## Running Tests

```bash
# All Python tests
pytest

# Verbose output with short tracebacks
pytest -v --tb=short
```

### Lambda Unit Tests

```bash
pytest app/lambdas/tests/ -v --tb=short
```

### ASL Validation

```bash
pytest app/step-functions-templates/tests/test_asl_validation.py -v --tb=short
```

### Run by Marker

```bash
# Only Lambda unit tests
pytest -m lambda_unit

# Only ASL validation
pytest -m asl_validation

# Only TestState API integration tests
pytest -m sfn_teststate

# Exclude tests requiring AWS credentials
pytest -m "not sfn_teststate"
```

## Markers

| Marker | Description | Requires |
|--------|-------------|----------|
| `lambda_unit` | Lambda function unit tests | — |
| `asl_validation` | ASL definition structural validation tests | — |
| `sfn_teststate` | Step Functions TestState API integration tests | AWS credentials with `states:TestState` permission |

Markers are enforced via `--strict-markers` in `pytest.ini`. Using an unregistered marker will cause an error.

## Post-Deployment Smoke Tests

Smoke tests are **not** part of the pytest suite. They are run as a standalone script during the CI/CD pipeline (CodeBuild step after deployment):

```bash
python3 smoke-tests/run-smoke-tests.py \
    --role-arn arn:aws:iam::ACCOUNT_ID:role/OrcaBusBeta-SmokeTestRole \
    --region ap-southeast-2
```

The smoke test runner discovers all deployed resources (Lambdas, state machines, SSM parameters) directly from the CloudFormation stacks and verifies:

- Lambda DryRun invocations succeed
- State machines are ACTIVE with no unresolved placeholders
- State machine IAM roles have required permissions (lambda:InvokeFunction, events:PutEvents, ssm:GetParameter)
- All SSM parameters referenced by state machines and Lambdas exist in the deployed stateful stack

See `smoke-tests/run-smoke-tests.py` and `smoke-tests/smoke-test-config.json` for details.

## TestState API Integration Tests

The `sfn_teststate` tests use the [AWS TestState API](https://docs.aws.amazon.com/step-functions/latest/dg/test-state-isolation.html) to validate individual state logic (JSONata expressions, Choice branching, data flow) against the real Step Functions service.

### How it works

The TestState API executes a single state from your ASL definition and returns the output, next state transition, and optionally intermediate data (after InputPath, after Parameters, etc.). When you provide a `mock` parameter for Task states, the API uses your mocked response instead of calling the actual downstream service (Lambda, SSM, EventBridge, etc.).

**Key point:** When a mock is provided, `roleArn` becomes optional — the service does not assume a role since no real downstream calls are made. This means you do not need any IAM role deployed, only AWS credentials that allow calling `states:TestState`.

### What these tests validate

- **Pass states:** Variable assignment via JSONata `Assign` expressions
- **Choice states:** Condition evaluation and correct branch routing
- **Task states:** Input/output processing (Arguments, Output extractors) with mocked service responses
- **Data flow:** That JSONata expressions correctly transform data between states

### Requirements

- AWS credentials (any credentials that allow calling `stepfunctions:TestState`)
- No IAM role ARN needed (mocks bypass downstream service calls)
- No deployed resources needed (state definitions are sent inline to the API)

### Running locally

```bash
# With AWS credentials configured (e.g. via AWS_PROFILE or env vars)
pytest -m sfn_teststate -v --tb=short

# Exclude from local runs (default workflow)
pytest -m "not sfn_teststate"
```

### Example test

```python
@pytest.mark.sfn_teststate
class TestChoiceBranching:
    def test_valid_draft_routes_to_validation(self, sfn_client, load_template):
        definition = load_template("validate_draft_data_and_put_ready_event_sfn_template")

        result = sfn_client.test_state(
            definition=definition,
            input_data={"isValid": True},
            state_name="Is Draft Event Complete?",
        )

        assertion = TestStateAssertion(result)
        assert assertion.assert_succeeded().passed
        assert assertion.assert_next_state("Run post-schema validation").passed
```

## Shared Fixtures

The following fixtures are provided automatically by the `orcabus-pipeline-test-utils` pytest plugin. No import is needed — they are auto-registered.

### `aws_mocks`

Session-scoped fixture providing pre-configured mock AWS clients via moto. Provides mocked clients for S3, SSM Parameter Store, Secrets Manager, and EventBridge.

```python
def test_ssm_read(aws_mocks):
    ssm_client = aws_mocks.ssm
    ssm_client.put_parameter(Name="/test/param", Value="hello", Type="String")
    response = ssm_client.get_parameter(Name="/test/param")
    assert response["Parameter"]["Value"] == "hello"
```

### `lambda_context`

Factory fixture returning a mock AWS Lambda context object with configurable attributes.

```python
def test_with_context(lambda_context):
    ctx = lambda_context(
        function_name="my-function",
        memory_limit_in_mb=512,
        aws_request_id="test-request-id"
    )
    assert ctx.function_name == "my-function"
    assert ctx.memory_limit_in_mb == 512
```

### `event_builder`

Factory fixture that wraps a dictionary payload into a Lambda event argument.

```python
def test_handler(event_builder, lambda_context):
    event = event_builder({"sample_id": "SMP001", "library_id": "LIB001"})
    ctx = lambda_context()
    result = handler(event, ctx)
    assert result["status"] == "success"
```

### SFN-Specific Fixtures (from `app/step-functions-templates/tests/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `load_template` | function | Factory to load and resolve ASL templates by name |
| `load_scenario` | function | Factory to load scenario JSON files by template and scenario name |
| `load_mock_config` | function | Factory to load `MockConfigFile.json` by template name |
| `teststate_client` | function | `TestStateClient` instance for TestState API tests |
| `assert_state` | function | Factory to create `TestStateAssertion` from a `TestStateResult` |
| `assert_path` | function | Factory to create `PathAssertion` from a list of `TestStateResult`s |

## Service-Specific Fixtures

The `app/lambdas/tests/conftest.py` provides service-specific constants:

| Fixture | Value | Purpose |
|---------|-------|---------|
| `service_name` | `"dragen-wgts-dna"` | Workflow service identifier |
| `event_source` | `"orcabus.dragenwgtsdna"` | EventBridge source |
| `event_bus_name` | `"OrcaBusMain"` | EventBridge bus name |
| `ssm_prefix` | `"/orcabus/workflows/dragen-wgts-dna/"` | SSM parameter prefix |

## Adding New Test Cases

### Adding a New Lambda Test

1. Create a new Lambda directory at `app/lambdas/<function_name>_py/`
2. Create a test file at `app/lambdas/tests/test_<function_name>.py`
3. Use the shared fixtures (`event_builder`, `lambda_context`, `aws_mocks`) — they are auto-registered via the `orcabus-pipeline-test-utils` plugin
4. If your Lambda uses a Lambda Layer dependency, mock it before importing the handler (see `examples/test_api_call_example.py`)

Example test structure:

```python
"""Tests for <function_name> Lambda."""

import sys
from pathlib import Path

import pytest

# Path setup for Lambda handler import
LAMBDA_DIR = Path(__file__).resolve().parents[1] / "<function_name>_py"
sys.path.insert(0, str(LAMBDA_DIR))

from <function_name> import handler  # noqa: E402


class TestHappyPath:
    def test_basic_invocation(self, event_builder, lambda_context):
        event = event_builder({"key": "value"})
        ctx = lambda_context(function_name="my-function")

        result = handler(event, ctx)

        assert result["status"] == "success"
```

If no corresponding `test_<function_name>.py` file exists for a Lambda module, pytest will emit a warning listing the untested functions (implemented in the root `conftest.py`).

### Adding a New SFN Test Scenario

1. Create a scenario JSON file at `app/step-functions-templates/tests/scenarios/<sfn_template_name>/<scenario_name>.json`:

```json
{
  "scenario_name": "happy_path",
  "description": "All steps complete successfully",
  "state_machine_template": "<template_name>.asl.json",
  "test_case_name": "HappyPath",
  "input": { "...": "..." },
  "expected_status": "SUCCEEDED",
  "expected_output": { "...": "..." },
  "expected_states_visited": ["State1", "State2"]
}
```

2. Create or update the `MockConfigFile.json` at `app/step-functions-templates/tests/mocks/<sfn_template_name>/MockConfigFile.json` with mocked responses for the new scenario:

```json
{
  "StateMachines": {
    "<state_machine_name>": {
      "TestCases": {
        "<TestCaseName>": {
          "<TaskStateName>": "<MockedResponseName>"
        }
      }
    }
  },
  "MockedResponses": {
    "<MockedResponseName>": {
      "0": {
        "Return": { "key": "value" }
      }
    }
  }
}
```

3. Write a test function in `app/step-functions-templates/tests/test_<sfn_template_name>.py` that uses the `load_scenario`, `load_template`, and `sfn_client` fixtures from `conftest.py`.

## CI Integration

### Pull Request Workflow (GitHub Actions)

Lambda unit tests and ASL validation run during PRs via the `pr-tests.yml` workflow in a dedicated `test-app` job that runs in parallel to `test-iac`. The job is conditional on `check-changes` detecting relevant file modifications. The `ci-gate` job requires both `test-iac` and `test-app` to pass before a PR can merge.

### Deployment Pipeline (CodePipeline)

The full test suite runs in the `unitAppTestConfig` stage of the `DeploymentStackPipeline` before deployment to Beta. This stage has AWS credentials available, so TestState API tests also run:

```bash
python3.14 -m pip install -r app/tests/requirements-test.txt --quiet
python3.14 -m pytest app/lambdas/tests/ -v --tb=short
python3.14 -m pytest app/step-functions-templates/tests/test_asl_validation.py -v --tb=short
python3.14 -m pytest app/step-functions-templates/tests/test_teststate_integration.py -v --tb=short
```
