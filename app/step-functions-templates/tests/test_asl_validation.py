"""ASL validation tests for service-dragen-wgts-dna-pipeline-manager.

Loads each ASL template from app/step-functions-templates/, resolves
placeholders, and validates structural correctness, state references,
and Lambda ARN cross-references against the CDK lambda configuration.

Requirements: 4.1, 4.3, 4.4
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orcabus_pipeline_test_utils.asl_validation import (
    ValidationCategory,
    check_lambda_arn_references,
    check_state_references,
    resolve_placeholders,
    validate_asl_definition,
)


# Paths relative to this test file
TESTS_DIR = Path(__file__).parent
TEMPLATES_DIR = TESTS_DIR.parent
APP_DIR = TEMPLATES_DIR.parent
SERVICE_ROOT = APP_DIR.parent
LAMBDA_CONFIG_PATH = TESTS_DIR / "lambda_config.json"

# Discover all .asl.json files in the templates directory
ASL_TEMPLATE_FILES = sorted(TEMPLATES_DIR.glob("*.asl.json"))


@pytest.fixture(scope="module")
def cdk_lambda_config() -> dict:
    """Load the CDK lambda configuration map."""
    assert LAMBDA_CONFIG_PATH.exists(), (
        f"lambda_config.json not found at {LAMBDA_CONFIG_PATH}. "
        "Create it to map Lambda ARN placeholders to CDK-defined functions."
    )
    return json.loads(LAMBDA_CONFIG_PATH.read_text())


@pytest.fixture(scope="module")
def resolved_templates() -> dict[str, dict]:
    """Load and resolve placeholders for all ASL templates.

    Returns a dict mapping template file name to parsed ASL JSON.
    """
    templates: dict[str, dict] = {}
    for template_path in ASL_TEMPLATE_FILES:
        raw_content = template_path.read_text()
        resolved_content = resolve_placeholders(raw_content)
        templates[template_path.name] = json.loads(resolved_content)
    return templates


class TestAslTemplateDiscovery:
    """Test that ASL templates are discoverable."""

    def test_at_least_one_template_exists(self):
        """Verify the templates directory contains at least one .asl.json file."""
        assert len(ASL_TEMPLATE_FILES) > 0, (
            f"No .asl.json files found in {TEMPLATES_DIR}"
        )

    def test_all_templates_are_valid_json(self):
        """Verify all ASL template files are parseable JSON."""
        for template_path in ASL_TEMPLATE_FILES:
            raw_content = template_path.read_text()
            try:
                json.loads(raw_content)
            except json.JSONDecodeError as e:
                pytest.fail(
                    f"Template {template_path.name} is not valid JSON: {e}"
                )


class TestAslStructuralValidation:
    """Test structural validation of each ASL template."""

    @pytest.mark.parametrize(
        "template_path",
        ASL_TEMPLATE_FILES,
        ids=[p.name for p in ASL_TEMPLATE_FILES],
    )
    def test_template_passes_structural_validation(
        self, template_path: Path
    ):
        """Each ASL template should pass structural validation after placeholder resolution."""
        raw_content = template_path.read_text()
        resolved_content = resolve_placeholders(raw_content)
        asl_json = json.loads(resolved_content)

        result = validate_asl_definition(asl_json, file_path=str(template_path))

        assert result.category == ValidationCategory.SUCCESS, (
            f"Template {template_path.name} failed validation with "
            f"category={result.category.value}:\n"
            + "\n".join(f"  - {e}" for e in result.errors)
        )


class TestStateReferences:
    """Test that all state references in ASL templates are valid."""

    @pytest.mark.parametrize(
        "template_path",
        ASL_TEMPLATE_FILES,
        ids=[p.name for p in ASL_TEMPLATE_FILES],
    )
    def test_template_has_valid_state_references(
        self, template_path: Path
    ):
        """All Next, Default, and Choice branch targets should reference existing states."""
        raw_content = template_path.read_text()
        resolved_content = resolve_placeholders(raw_content)
        asl_json = json.loads(resolved_content)

        errors = check_state_references(asl_json)

        assert errors == [], (
            f"Template {template_path.name} has dangling state references:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


class TestLambdaArnReferences:
    """Test that all Lambda ARN placeholders are defined in the CDK lambda config."""

    @pytest.mark.parametrize(
        "template_path",
        ASL_TEMPLATE_FILES,
        ids=[p.name for p in ASL_TEMPLATE_FILES],
    )
    def test_template_lambda_arns_are_in_config(
        self, template_path: Path, cdk_lambda_config: dict
    ):
        """Every Lambda ARN placeholder in the template should have a CDK config entry."""
        raw_content = template_path.read_text()
        # Parse the raw (unresolved) content to find placeholders
        asl_json = json.loads(resolve_placeholders(raw_content))

        # We need to check against the raw content for Lambda ARN placeholders,
        # so re-parse without resolution for the cross-reference check
        raw_asl_json = json.loads(raw_content)

        errors = check_lambda_arn_references(raw_asl_json, cdk_lambda_config)

        assert errors == [], (
            f"Template {template_path.name} has unresolved Lambda ARN placeholders:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_lambda_config_entries_have_valid_paths(
        self, cdk_lambda_config: dict
    ):
        """Each entry in lambda_config.json should point to an existing Lambda directory."""
        lambdas = cdk_lambda_config.get("lambdas", {})

        for lambda_name, lambda_info in lambdas.items():
            entry_path = SERVICE_ROOT / lambda_info["entry"]
            assert entry_path.exists(), (
                f"Lambda config entry '{lambda_name}' references "
                f"non-existent path: {lambda_info['entry']}"
            )

    def test_lambda_config_covers_all_asl_placeholders(
        self, cdk_lambda_config: dict
    ):
        """The lambda_config.json should cover all Lambda ARN placeholders across all templates."""
        import re

        pattern = re.compile(r"\$\{__([a-z0-9_]+_lambda_function_arn)__\}")

        all_placeholders: set[str] = set()
        for template_path in ASL_TEMPLATE_FILES:
            raw_content = template_path.read_text()
            found = pattern.findall(raw_content)
            for inner_name in found:
                all_placeholders.add(f"${{__{inner_name}__}}")

        known_placeholders: set[str] = set()
        for lambda_info in cdk_lambda_config.get("lambdas", {}).values():
            if "placeholder" in lambda_info:
                known_placeholders.add(lambda_info["placeholder"])

        missing = all_placeholders - known_placeholders
        assert missing == set(), (
            f"Lambda ARN placeholders not covered in lambda_config.json:\n"
            + "\n".join(f"  - {p}" for p in sorted(missing))
        )
