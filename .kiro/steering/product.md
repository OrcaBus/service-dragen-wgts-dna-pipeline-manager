# Product: Dragen WGTS DNA Pipeline Manager

## Summary

This is an OrcaBus microservice that manages the lifecycle of the **Dragen WGTS DNA pipeline** — Illumina's DRAGEN-based whole genome sequencing pipeline for germline and somatic DNA analysis (alignment + variant calling).

The service handles orchestration on ICAv2 (Illumina Connected Analytics v2) via CWL workflows. It follows the standard ICAv2-centric Pipeline Architecture used across OrcaBus.

## Core Responsibilities

- Accept `WorkflowRunStateChange` DRAFT events and validate/populate them into READY events
- Submit READY events to ICAv2 as `Icav2WesRequest` events via a Step Functions state machine
- Monitor ICAv2 analysis state changes and convert them to `WorkflowRunUpdate` events
- Validate draft schemas against a registered JSON schema before promotion

## Event Flow

```
DRAFT event (WorkflowRunStateChange)
  → populate draft data (Step Functions)
  → validate draft schema
  → emit READY event
  → submit to ICAv2 WES
  → monitor ICAv2 state changes
  → emit WorkflowRunUpdate events
```

## Upstream / Downstream

- **Upstream**: Analysis Glue
- **Downstream**: Oncoanalyser WGTS DNA, Oncoanalyser WGTS DNA/RNA
- **Key dependencies**: ICAv2 WES Manager, Workflow Manager, Fastq Glue

## Environments

Deploys to `beta`, `gamma`, and `prod` via AWS CodePipeline. The toolchain account hosts the CodePipeline; application stacks deploy cross-account.
