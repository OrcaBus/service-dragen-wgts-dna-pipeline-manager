"""
Root conftest.py for pytest configuration.

Implements untested Lambda detection: compares app/lambdas/ directories
(ending in _py) against test files in app/lambdas/tests/ and emits a
warning listing Lambda functions without corresponding test files.
"""

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Detect Lambda modules without corresponding test files and emit warnings."""
    root_dir = Path(config.rootdir)
    lambdas_dir = root_dir / "app" / "lambdas"
    tests_dir = lambdas_dir / "tests"

    if not lambdas_dir.is_dir():
        return

    # Find all Lambda module directories (ending in _py, excluding tests/ and __pycache__/)
    lambda_modules: list[str] = []
    excluded_dirs = {"tests", "__pycache__"}
    for entry in sorted(lambdas_dir.iterdir()):
        if (
            entry.is_dir()
            and entry.name.endswith("_py")
            and entry.name not in excluded_dirs
        ):
            lambda_modules.append(entry.name)

    if not lambda_modules:
        return

    # Determine which Lambda modules have corresponding test files
    # Convention: directory `foo_bar_py` -> test file `test_foo_bar.py`
    untested_modules: list[str] = []
    for module_dir_name in lambda_modules:
        # Strip the _py suffix to get the module name
        module_name = module_dir_name.removesuffix("_py")
        expected_test_file = tests_dir / f"test_{module_name}.py"
        if not expected_test_file.is_file():
            untested_modules.append(module_dir_name)

    if untested_modules:
        modules_list = "\n  - ".join(untested_modules)
        config.issue_config_time_warning(
            pytest.PytestWarning(
                f"Lambda functions without test files:\n  - {modules_list}\n"
                f"Expected test files in: {tests_dir.relative_to(root_dir)}/"
            ),
            stacklevel=1,
        )
