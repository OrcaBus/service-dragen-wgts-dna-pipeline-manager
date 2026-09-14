"""Service-specific test fixtures for service-dragen-wgts-dna-pipeline-manager.

The shared plugin fixtures (AWS mocks, lambda_context, event_builder) are
auto-registered via the orcabus_pipeline_test_utils pytest plugin entry point.
No explicit import of those fixtures is needed here.

This file provides service-specific fixtures for dragen-wgts-dna tests.
"""

import pytest


# -- Service-specific constants ------------------------------------------------

SERVICE_NAME = "dragen-wgts-dna"
EVENT_SOURCE = "orcabus.dragenwgtsdna"
EVENT_BUS_NAME = "OrcaBusMain"
SSM_PREFIX = "/orcabus/workflows/dragen-wgts-dna/"


# -- Service-specific fixtures -------------------------------------------------


@pytest.fixture
def service_name() -> str:
    """Return the workflow service name for dragen-wgts-dna."""
    return SERVICE_NAME


@pytest.fixture
def event_source() -> str:
    """Return the EventBridge event source for dragen-wgts-dna."""
    return EVENT_SOURCE


@pytest.fixture
def event_bus_name() -> str:
    """Return the EventBridge event bus name."""
    return EVENT_BUS_NAME


@pytest.fixture
def ssm_prefix() -> str:
    """Return the SSM parameter prefix for dragen-wgts-dna."""
    return SSM_PREFIX
