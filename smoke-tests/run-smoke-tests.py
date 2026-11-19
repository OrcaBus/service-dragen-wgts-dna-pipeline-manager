#!/usr/bin/env python3
"""Post-deployment smoke test runner.

Discovers deployed Lambda functions, state machines, and SSM parameters from
CloudFormation stacks and runs smoke checks to verify they are correctly
deployed, accessible, and properly wired.

This script is designed to run as a CodeBuild step after Beta/Gamma deployment
in the CI/CD pipeline. It uses assumed-role credentials for cross-account access.

Usage:
    python3 smoke-tests/run-smoke-tests.py \
        --role-arn arn:aws:iam::843407916570:role/OrcaBusBeta-SmokeTestRole \
        --region ap-southeast-2 \
        --timeout 120

Environment variables:
    AWS_DEFAULT_REGION: The AWS region to use (fallback if --region not specified)

Exit codes:
    0: All smoke tests passed
    1: One or more smoke tests failed
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


# Auth-related error codes
_AUTH_ERROR_CODES = {"AccessDeniedException", "ExpiredTokenException"}

# Regex to detect unresolved placeholders in state machine definitions
_PLACEHOLDER_PATTERN = re.compile(r"__[a-z][a-z0-9_]*__")


class SmokeTestResult:
    """Result of a single smoke test check."""

    def __init__(
        self,
        resource_name: str,
        resource_type: str,
        passed: bool,
        error_type: str | None = None,
        error_message: str | None = None,
    ):
        self.resource_name = resource_name
        self.resource_type = resource_type
        self.passed = passed
        self.error_type = error_type
        self.error_message = error_message


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def discover_stack_resources(
    stack_name: str,
    resource_type: str,
    session: boto3.Session,
) -> list[str]:
    """Discover deployed resources of a given type from a CloudFormation stack.

    Returns a list of physical resource IDs.
    """
    client = session.client("cloudformation")
    physical_ids: list[str] = []

    try:
        paginator = client.get_paginator("list_stack_resources")
        for page in paginator.paginate(StackName=stack_name):
            for resource in page.get("StackResourceSummaries", []):
                if resource["ResourceType"] == resource_type:
                    physical_id = resource.get("PhysicalResourceId")
                    if physical_id:
                        physical_ids.append(physical_id)
    except ClientError as e:
        print(
            f"  ERROR: Failed to list stack resources for '{stack_name}': {e}",
            file=sys.stderr,
        )

    return physical_ids


def discover_lambda_functions(stack_name: str, session: boto3.Session) -> list[str]:
    """Discover Lambda function names from the stateless CloudFormation stack."""
    return discover_stack_resources(stack_name, "AWS::Lambda::Function", session)


def discover_state_machines(stack_name: str, session: boto3.Session) -> list[str]:
    """Discover state machine ARNs from the stateless CloudFormation stack."""
    return discover_stack_resources(stack_name, "AWS::StepFunctions::StateMachine", session)


def discover_ssm_parameters(stack_name: str, session: boto3.Session) -> list[str]:
    """Discover SSM parameter names from the stateful CloudFormation stack."""
    return discover_stack_resources(stack_name, "AWS::SSM::Parameter", session)


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_lambda_invocable(function_name: str, session: boto3.Session) -> SmokeTestResult:
    """Perform a DryRun invocation of a Lambda function and verify HTTP 204."""
    client = session.client("lambda")

    try:
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="DryRun",
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        error_type = "auth" if error_code in _AUTH_ERROR_CODES else "config"
        return SmokeTestResult(
            resource_name=function_name,
            resource_type="lambda",
            passed=False,
            error_type=error_type,
            error_message=f"{error_code}: {error_message}",
        )
    except Exception as e:
        return SmokeTestResult(
            resource_name=function_name,
            resource_type="lambda",
            passed=False,
            error_type="config",
            error_message=str(e),
        )

    status_code = response.get("StatusCode", 0)
    if status_code == 204:
        return SmokeTestResult(
            resource_name=function_name,
            resource_type="lambda",
            passed=True,
        )

    return SmokeTestResult(
        resource_name=function_name,
        resource_type="lambda",
        passed=False,
        error_type="config",
        error_message=f"Expected HTTP 204, got {status_code}",
    )


def check_state_machine_active(state_machine_arn: str, session: boto3.Session) -> SmokeTestResult:
    """Call DescribeStateMachine, verify status=ACTIVE and definition non-null."""
    client = session.client("stepfunctions")

    try:
        response = client.describe_state_machine(stateMachineArn=state_machine_arn)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        error_type = "auth" if error_code in _AUTH_ERROR_CODES else "config"
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine",
            passed=False,
            error_type=error_type,
            error_message=f"{error_code}: {error_message}",
        )
    except Exception as e:
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine",
            passed=False,
            error_type="config",
            error_message=str(e),
        )

    status = response.get("status")
    definition = response.get("definition")

    if status != "ACTIVE":
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine",
            passed=False,
            error_type="config",
            error_message=f"State machine status is '{status}', expected 'ACTIVE'",
        )

    if not definition:
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine",
            passed=False,
            error_type="config",
            error_message="State machine definition is null or empty",
        )

    return SmokeTestResult(
        resource_name=state_machine_arn,
        resource_type="state_machine",
        passed=True,
    )


def check_state_machine_no_placeholders(
    state_machine_arn: str, session: boto3.Session
) -> SmokeTestResult:
    """Verify the deployed state machine definition has no unresolved __placeholder__ tokens."""
    client = session.client("stepfunctions")

    try:
        response = client.describe_state_machine(stateMachineArn=state_machine_arn)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        error_type = "auth" if error_code in _AUTH_ERROR_CODES else "config"
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine_definition",
            passed=False,
            error_type=error_type,
            error_message=f"{error_code}: {error_message}",
        )

    definition = response.get("definition", "")
    placeholders = _PLACEHOLDER_PATTERN.findall(definition)

    if placeholders:
        unique = sorted(set(placeholders))
        return SmokeTestResult(
            resource_name=state_machine_arn,
            resource_type="state_machine_definition",
            passed=False,
            error_type="config",
            error_message=f"Unresolved placeholders: {', '.join(unique)}",
        )

    return SmokeTestResult(
        resource_name=state_machine_arn,
        resource_type="state_machine_definition",
        passed=True,
    )


def check_state_machine_permissions(
    state_machine_arn: str,
    expected_actions: list[str],
    session: boto3.Session,
) -> list[SmokeTestResult]:
    """Verify the state machine's IAM role has the expected permissions.

    Fetches the role attached to the state machine, then inspects its inline
    and attached policies for the required actions.
    """
    sfn_client = session.client("stepfunctions")
    iam_client = session.client("iam")
    results: list[SmokeTestResult] = []

    # Get the role ARN from the state machine
    try:
        response = sfn_client.describe_state_machine(stateMachineArn=state_machine_arn)
    except ClientError as e:
        results.append(
            SmokeTestResult(
                resource_name=state_machine_arn,
                resource_type="state_machine_permissions",
                passed=False,
                error_type=(
                    "auth" if e.response["Error"]["Code"] in _AUTH_ERROR_CODES else "config"
                ),
                error_message=f"Cannot describe state machine: {e.response['Error']['Message']}",
            )
        )
        return results

    role_arn = response.get("roleArn", "")
    if not role_arn:
        results.append(
            SmokeTestResult(
                resource_name=state_machine_arn,
                resource_type="state_machine_permissions",
                passed=False,
                error_type="config",
                error_message="State machine has no roleArn",
            )
        )
        return results

    # Extract role name from ARN (arn:aws:iam::ACCOUNT:role/ROLE_NAME)
    role_name = role_arn.split("/")[-1]

    # Collect all actions from inline policies
    granted_actions: set[str] = set()
    try:
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in inline_policies.get("PolicyNames", []):
            policy_response = iam_client.get_role_policy(
                RoleName=role_name, PolicyName=policy_name
            )
            policy_doc = policy_response.get("PolicyDocument", {})
            for statement in policy_doc.get("Statement", []):
                if statement.get("Effect") == "Allow":
                    action = statement.get("Action", [])
                    if isinstance(action, str):
                        granted_actions.add(action)
                    elif isinstance(action, list):
                        granted_actions.update(action)
    except ClientError as e:
        results.append(
            SmokeTestResult(
                resource_name=state_machine_arn,
                resource_type="state_machine_permissions",
                passed=False,
                error_type=(
                    "auth" if e.response["Error"]["Code"] in _AUTH_ERROR_CODES else "config"
                ),
                error_message=(
                    f"Cannot read role policies for {role_name}: "
                    f"{e.response['Error']['Message']}"
                ),
            )
        )
        return results

    # Also check attached managed policies
    try:
        attached = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in attached.get("AttachedPolicies", []):
            policy_arn = policy["PolicyArn"]
            version_response = iam_client.get_policy(PolicyArn=policy_arn)
            version_id = version_response["Policy"]["DefaultVersionId"]
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn, VersionId=version_id
            )
            policy_doc = policy_version["PolicyVersion"]["Document"]
            for statement in policy_doc.get("Statement", []):
                if statement.get("Effect") == "Allow":
                    action = statement.get("Action", [])
                    if isinstance(action, str):
                        granted_actions.add(action)
                    elif isinstance(action, list):
                        granted_actions.update(action)
    except ClientError:
        # Managed policy read may fail due to permissions — not critical
        pass

    # Check each expected action
    sm_name = state_machine_arn.split(":")[-1]
    for expected_action in expected_actions:
        has_permission = any(
            _action_matches(expected_action, granted) for granted in granted_actions
        )
        if has_permission:
            results.append(
                SmokeTestResult(
                    resource_name=f"{sm_name} -> {expected_action}",
                    resource_type="state_machine_permissions",
                    passed=True,
                )
            )
        else:
            results.append(
                SmokeTestResult(
                    resource_name=f"{sm_name} -> {expected_action}",
                    resource_type="state_machine_permissions",
                    passed=False,
                    error_type="config",
                    error_message=f"Missing permission '{expected_action}' on role {role_name}",
                )
            )

    return results


def _action_matches(expected: str, granted: str) -> bool:
    """Check if a granted action covers the expected action.

    Handles exact matches and wildcard patterns like 'lambda:*' or '*'.
    """
    if granted == "*":
        return True
    if granted == expected:
        return True
    # Handle service-level wildcards like "lambda:*"
    if granted.endswith(":*"):
        service = granted[:-2]
        return expected.startswith(service + ":")
    return False


def check_ssm_parameter_exists(parameter_path: str, session: boto3.Session) -> SmokeTestResult:
    """Verify an SSM parameter exists and is readable."""
    client = session.client("ssm")

    try:
        client.get_parameter(Name=parameter_path, WithDecryption=True)
        return SmokeTestResult(
            resource_name=parameter_path,
            resource_type="ssm_parameter",
            passed=True,
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))
        error_type = "auth" if error_code in _AUTH_ERROR_CODES else "config"
        return SmokeTestResult(
            resource_name=parameter_path,
            resource_type="ssm_parameter",
            passed=False,
            error_type=error_type,
            error_message=error_message,
        )


def extract_ssm_references_from_definition(
    definition: str, ssm_prefix: str
) -> set[str]:
    """Extract SSM parameter paths referenced in a state machine definition.

    Looks for string values that start with the given SSM prefix.
    This catches parameters used in SSM GetParameter calls within ASL.
    """
    # Match quoted strings that look like SSM parameter paths
    pattern = re.compile(re.escape(ssm_prefix) + r"[a-zA-Z0-9/_-]+")
    return set(pattern.findall(definition))


def extract_ssm_references_from_lambda_env(
    function_name: str, ssm_prefix: str, session: boto3.Session
) -> set[str]:
    """Extract SSM parameter paths from a Lambda function's environment variables."""
    client = session.client("lambda")
    refs: set[str] = set()

    try:
        response = client.get_function_configuration(FunctionName=function_name)
        env_vars = response.get("Environment", {}).get("Variables", {})
        pattern = re.compile(re.escape(ssm_prefix) + r"[a-zA-Z0-9/_-]+")
        for value in env_vars.values():
            refs.update(pattern.findall(value))
    except ClientError:
        pass

    return refs


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def assume_role(role_arn: str, region: str) -> boto3.Session:
    """Assume a cross-account role and return a session with temporary credentials."""
    sts_client = boto3.client("sts", region_name=region)

    try:
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="SmokeTestSession",
            DurationSeconds=900,
        )
    except ClientError as e:
        print(f"ERROR: Failed to assume role {role_arn}: {e}", file=sys.stderr)
        sys.exit(1)

    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    )


def timeout_handler(signum: int, frame: object) -> None:
    """Handle timeout signal."""
    print("\nERROR: Smoke test execution exceeded timeout limit", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-deployment smoke tests")
    parser.add_argument(
        "--config",
        default="smoke-tests/smoke-test-config.json",
        help="Path to smoke test configuration JSON file (default: smoke-tests/smoke-test-config.json)",
    )
    parser.add_argument(
        "--role-arn",
        required=False,
        help="IAM role ARN to assume for cross-account access (optional if running locally)",
    )
    parser.add_argument(
        "--region",
        default="ap-southeast-2",
        help="AWS region (default: ap-southeast-2)",
    )
    parser.add_argument(
        "--stage",
        default="Beta",
        choices=["Beta", "Gamma", "Prod"],
        help="Deployment stage name used to resolve stack names (default: Beta)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds for smoke test execution (default: 120)",
    )
    args = parser.parse_args()

    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.timeout)

    start_time = time.time()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1

    with open(config_path) as f:
        config = json.load(f)

    # Resolve stage placeholder
    stage_prefix = f"OrcaBus{args.stage}"
    stateless_stack_name = config["stateless_stack_name"].replace("{stage_prefix}", stage_prefix)
    stateful_stack_name = config["stateful_stack_name"].replace("{stage_prefix}", stage_prefix)
    ssm_parameter_prefix = config.get("ssm_parameter_prefix", "")
    expected_lambda_count = config.get("expected_lambda_count")
    expected_state_machine_count = config.get("expected_state_machine_count")
    state_machine_permissions = config.get("state_machine_permissions", {})

    # Get session (either assumed role or default)
    if args.role_arn:
        print(f"Assuming role: {args.role_arn}")
        session = assume_role(args.role_arn, args.region)
    else:
        session = boto3.Session(region_name=args.region)

    # Get account ID
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    print(f"Running smoke tests in account: {account_id}, region: {args.region}")
    print(f"Stateless stack: {stateless_stack_name}")
    print(f"Stateful stack:  {stateful_stack_name}")
    print("-" * 60)

    results: list[SmokeTestResult] = []

    # -----------------------------------------------------------------------
    # 1. Discover resources from CloudFormation stacks
    # -----------------------------------------------------------------------

    print("\n[Discovery - Stateless Stack Resources]")
    lambda_functions = discover_lambda_functions(stateless_stack_name, session)
    state_machine_arns = discover_state_machines(stateless_stack_name, session)
    print(f"  Lambda functions:  {len(lambda_functions)}")
    print(f"  State machines:    {len(state_machine_arns)}")

    print("\n[Discovery - Stateful Stack Resources]")
    ssm_parameters = discover_ssm_parameters(stateful_stack_name, session)
    print(f"  SSM parameters:    {len(ssm_parameters)}")

    # -----------------------------------------------------------------------
    # 2. Validate expected counts
    # -----------------------------------------------------------------------

    print("\n[Resource Counts]")
    if expected_lambda_count is not None:
        count_ok = len(lambda_functions) == expected_lambda_count
        status = "PASS" if count_ok else "FAIL"
        msg = f"Lambda count: {len(lambda_functions)} (expected {expected_lambda_count})"
        print(f"  [{status}] {msg}")
        results.append(
            SmokeTestResult(
                resource_name="lambda_count",
                resource_type="count_check",
                passed=count_ok,
                error_type=None if count_ok else "config",
                error_message=None if count_ok else msg,
            )
        )

    if expected_state_machine_count is not None:
        count_ok = len(state_machine_arns) == expected_state_machine_count
        status = "PASS" if count_ok else "FAIL"
        msg = f"State machine count: {len(state_machine_arns)} (expected {expected_state_machine_count})"
        print(f"  [{status}] {msg}")
        results.append(
            SmokeTestResult(
                resource_name="state_machine_count",
                resource_type="count_check",
                passed=count_ok,
                error_type=None if count_ok else "config",
                error_message=None if count_ok else msg,
            )
        )

    # -----------------------------------------------------------------------
    # 3. Lambda DryRun invocations
    # -----------------------------------------------------------------------

    print("\n[Lambda Functions - DryRun Invocation]")
    if lambda_functions:
        for func_name in sorted(lambda_functions):
            result = check_lambda_invocable(func_name, session)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {func_name}")
            if not result.passed:
                print(f"         Error ({result.error_type}): {result.error_message}")
    else:
        print("  WARNING: No Lambda functions discovered")

    # -----------------------------------------------------------------------
    # 4. State Machines - Active status
    # -----------------------------------------------------------------------

    print("\n[State Machines - DescribeStateMachine]")
    for arn in state_machine_arns:
        result = check_state_machine_active(arn, session)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        sm_name = arn.split(":")[-1]
        print(f"  [{status}] {sm_name}")
        if not result.passed:
            print(f"         Error ({result.error_type}): {result.error_message}")

    # -----------------------------------------------------------------------
    # 5. State Machines - No unresolved placeholders
    # -----------------------------------------------------------------------

    print("\n[State Machines - No Unresolved Placeholders]")
    for arn in state_machine_arns:
        result = check_state_machine_no_placeholders(arn, session)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        sm_name = arn.split(":")[-1]
        print(f"  [{status}] {sm_name}")
        if not result.passed:
            print(f"         Error ({result.error_type}): {result.error_message}")

    # -----------------------------------------------------------------------
    # 6. State Machines - IAM Permissions
    # -----------------------------------------------------------------------

    if state_machine_permissions:
        print("\n[State Machines - IAM Permissions]")
        for arn in state_machine_arns:
            sm_name = arn.split(":")[-1]
            # Extract logical name from physical name (prefix--logicalName)
            logical_name = sm_name.split("--", 1)[-1] if "--" in sm_name else sm_name
            expected_actions = state_machine_permissions.get(logical_name, [])
            if not expected_actions:
                continue
            perm_results = check_state_machine_permissions(arn, expected_actions, session)
            for result in perm_results:
                results.append(result)
                status = "PASS" if result.passed else "FAIL"
                print(f"  [{status}] {result.resource_name}")
                if not result.passed:
                    print(f"         Error ({result.error_type}): {result.error_message}")

    # -----------------------------------------------------------------------
    # 7. SSM Parameters - Verify all deployed parameters are readable
    # -----------------------------------------------------------------------

    print("\n[SSM Parameters - GetParameter]")
    if ssm_parameters:
        for param_path in sorted(ssm_parameters):
            result = check_ssm_parameter_exists(param_path, session)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {param_path}")
            if not result.passed:
                print(f"         Error ({result.error_type}): {result.error_message}")
    else:
        print("  WARNING: No SSM parameters discovered from stateful stack")

    # -----------------------------------------------------------------------
    # 8. SSM Cross-Reference - Verify parameters referenced by state machines
    #    and Lambdas exist in the deployed stateful stack
    # -----------------------------------------------------------------------

    if ssm_parameter_prefix and ssm_parameters:
        print("\n[SSM Cross-Reference - Referenced Parameters Exist]")
        deployed_params = set(ssm_parameters)
        referenced_params: set[str] = set()

        # Collect SSM references from state machine definitions
        sfn_client = session.client("stepfunctions")
        for arn in state_machine_arns:
            try:
                resp = sfn_client.describe_state_machine(stateMachineArn=arn)
                definition = resp.get("definition", "")
                referenced_params.update(
                    extract_ssm_references_from_definition(definition, ssm_parameter_prefix)
                )
            except ClientError:
                pass

        # Collect SSM references from Lambda environment variables
        for func_name in lambda_functions:
            referenced_params.update(
                extract_ssm_references_from_lambda_env(func_name, ssm_parameter_prefix, session)
            )

        # Check each referenced parameter exists in the deployed set
        if referenced_params:
            for ref_param in sorted(referenced_params):
                # The reference might be a prefix (e.g. for versioned params like
                # /orcabus/workflows/dragen-wgts-dna/inputs-by-workflow-version)
                # Check if it matches exactly or if any deployed param starts with it
                exact_match = ref_param in deployed_params
                prefix_match = any(p.startswith(ref_param) for p in deployed_params)

                passed = exact_match or prefix_match
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {ref_param}")
                if not passed:
                    print(f"         Not found in stateful stack SSM parameters")
                results.append(
                    SmokeTestResult(
                        resource_name=ref_param,
                        resource_type="ssm_cross_reference",
                        passed=passed,
                        error_type=None if passed else "config",
                        error_message=(
                            None
                            if passed
                            else f"SSM parameter '{ref_param}' referenced but not deployed"
                        ),
                    )
                )
        else:
            print("  No SSM parameter references found in state machines or Lambdas")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    elapsed = time.time() - start_time
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"Smoke Test Results: {passed}/{total} passed, {failed} failed ({elapsed:.1f}s)")

    if failed > 0:
        auth_failures = [r for r in results if not r.passed and r.error_type == "auth"]
        config_failures = [r for r in results if not r.passed and r.error_type == "config"]

        if auth_failures:
            print(f"\n  Authentication/Authorization failures: {len(auth_failures)}")
            for r in auth_failures:
                print(f"    - {r.resource_type}/{r.resource_name}: {r.error_message}")

        if config_failures:
            print(f"\n  Configuration failures: {len(config_failures)}")
            for r in config_failures:
                print(f"    - {r.resource_type}/{r.resource_name}: {r.error_message}")

        print("\nSMOKE TESTS FAILED - halting promotion to next environment")
        return 1

    print("\nAll smoke tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
