# Test Documentation

This document provides the high-level test directory layout for `service-dragen-wgts-dna-pipeline-manager`. For detailed Python test documentation (fixtures, markers, how to add tests, CI), see [app/tests/README.md](app/tests/README.md).

## Test Directory Layout

```
service-dragen-wgts-dna-pipeline-manager/
├── conftest.py                              # Root conftest — untested Lambda detection warnings
├── pytest.ini                               # pytest configuration (markers, test paths, options)
├── app/
│   └── tests/
│       ├── requirements-test.txt            # Python test dependencies (shared across all app tests)
│       └── README.md                        # Detailed Python test documentation
├── app/lambdas/tests/                       # Lambda unit tests (Python)
├── app/step-functions-templates/tests/      # ASL validation + SFN Local integration tests (Python)
├── smoke-tests/                             # Post-deployment smoke tests (Python)
│   ├── run-smoke-tests.py                   # Smoke test runner script
│   └── smoke-test-config.json               # Configuration (stack names, expected counts, permissions)
└── test/                                    # CDK/Jest infrastructure tests (TypeScript)
    ├── stage.test.ts
    ├── toolchain.test.ts
    └── utils.ts
```

## Test Categories

| Category              | Language   | Location                              | Runner          | When                          |
| --------------------- | ---------- | ------------------------------------- | --------------- | ----------------------------- |
| Lambda unit tests     | Python     | `app/lambdas/tests/`                  | pytest          | PR / pre-merge                |
| ASL validation        | Python     | `app/step-functions-templates/tests/` | pytest          | PR / pre-merge                |
| SFN Local integration | Python     | `app/step-functions-templates/tests/` | pytest + Docker | PR / pre-merge                |
| CDK infrastructure    | TypeScript | `test/`                               | Jest            | PR / pre-merge                |
| Smoke tests           | Python     | `smoke-tests/`                        | CodeBuild       | Post-deployment (Beta, Gamma) |

## Quick Start

```bash
# Python tests — install dependencies then run
pip install -r app/tests/requirements-test.txt
pytest

# CDK/Jest tests
pnpm test

# Smoke tests (run locally against a deployed environment)
python3 smoke-tests/run-smoke-tests.py --stage Beta --region ap-southeast-2
```

## Smoke Tests

Smoke tests run after deployment to Beta and Gamma environments as a CodeBuild step in the CI/CD pipeline. They verify that deployed resources are correctly provisioned, accessible, and properly wired together.

### When They Run

The smoke tests are integrated into the `StatelessDragenWgtsDnaPipeline` CodePipeline:

1. Code merges to `main`
2. CDK synth + unit tests pass
3. **Deploy to Beta** → **Smoke tests run against Beta**
4. **Deploy to Gamma** → **Smoke tests run against Gamma**
5. Deploy to Prod (no smoke tests — validated in prior stages)

If smoke tests fail, the pipeline halts and the deployment does not promote to the next environment.

### What They Check

The smoke test discovers all resources from CloudFormation stacks rather than maintaining a hardcoded list:

| Check                          | Description                                                                                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Resource discovery**         | Queries `{stage}-StatelessDragenWgtsDnaPipelineManager` and `{stage}-StatefulDragenWgtsDnaPipeline` stacks via CloudFormation `ListStackResources`                  |
| **Resource counts**            | Verifies expected number of Lambdas (22) and state machines (4) are deployed                                                                                        |
| **Lambda DryRun**              | Invokes each Lambda with `InvocationType=DryRun` to confirm it's reachable and returns HTTP 204                                                                     |
| **State machine status**       | Calls `DescribeStateMachine` and verifies `status=ACTIVE` with a non-null definition                                                                                |
| **No unresolved placeholders** | Scans each state machine definition for `__placeholder__` tokens that should have been substituted by CDK                                                           |
| **IAM permissions**            | Inspects each state machine's IAM role policies to confirm expected actions are granted (`lambda:InvokeFunction`, `events:PutEvents`, `ssm:GetParameter`)           |
| **SSM parameter readability**  | Reads each SSM parameter discovered from the stateful stack                                                                                                         |
| **SSM cross-reference**        | Extracts SSM parameter paths referenced in state machine definitions and Lambda environment variables, then verifies each one exists in the deployed stateful stack |

### Configuration

The configuration lives in `smoke-tests/smoke-test-config.json`:

```json
{
  "stateless_stack_name": "{stage_prefix}-StatelessDragenWgtsDnaPipelineManager",
  "stateful_stack_name": "{stage_prefix}-StatefulDragenWgtsDnaPipeline",
  "expected_lambda_count": 22,
  "expected_state_machine_count": 4,
  "ssm_parameter_prefix": "/orcabus/workflows/dragen-wgts-dna/",
  "state_machine_permissions": {
    "populateDraftData": ["lambda:InvokeFunction", "ssm:GetParameter", "events:PutEvents"],
    "validateDraftDataAndPutReadyEvent": ["lambda:InvokeFunction", "events:PutEvents"],
    "readyEventToIcav2WesRequestEvent": ["lambda:InvokeFunction", "events:PutEvents"],
    "icav2WesEventToWrscEvent": ["lambda:InvokeFunction", "events:PutEvents"]
  }
}
```

The `{stage_prefix}` placeholder is resolved at runtime based on the `--stage` argument (e.g. `OrcaBusBeta`, `OrcaBusGamma`).

### Running Locally

```bash
# Using default AWS credentials (must have access to the target account)
python3 smoke-tests/run-smoke-tests.py --stage Beta

# With cross-account role assumption
python3 smoke-tests/run-smoke-tests.py \
    --role-arn arn:aws:iam::ACCOUNT_ID:role/OrcaBusBeta-CrossAccountSmokeTestRole \
    --stage Beta \
    --region ap-southeast-2
```

### Required IAM Permissions (Cross-Account Role)

The smoke test role in the target account needs:

- `cloudformation:ListStackResources` — discover resources from stacks
- `lambda:InvokeFunction` (DryRun) — validate Lambda accessibility
- `lambda:GetFunctionConfiguration` — read environment variables for SSM cross-referencing
- `states:DescribeStateMachine` — check state machine status and definition
- `ssm:GetParameter` — verify SSM parameters are readable
- `iam:ListRolePolicies`, `iam:GetRolePolicy` — inspect state machine role inline policies
- `iam:ListAttachedRolePolicies`, `iam:GetPolicy`, `iam:GetPolicyVersion` — inspect managed policies
