# Step Functions Standards

Standards for AWS Step Functions design across all OrcaBus pipeline manager services.

## DRAFT Event Regeneration

If any of the following change during the populate-draft-data state machine, a **new DRAFT event must be emitted** before proceeding to populate inputs:

- Engine parameters (`projectId`, `pipelineId`, `outputUri`, `logsUri`)
- Tags (`libraryId`, `tumorLibraryId`, `subjectId`, etc.)

This is critical because input population (e.g. waiting for FASTQ data to become available) can take up to 48 hours — for example, waiting for a sequencing run to finish or data to be extracted from archive. The new DRAFT event ensures the Workflow Manager record stays in sync with the current state throughout this period.

### Pattern (from dragen-wgts-dna)

```
1. Resolve engine parameters + tags
2. Compare with original event values
3. IF changed → emit WorkflowRunUpdate DRAFT event with updated payload
4. THEN continue to resolve inputs (which may block on task tokens)
```

## Lambda Versioning in Step Functions

- Use `$LATEST` version qualifier when invoking Lambdas from Step Functions
- This enables redriving failed executions after fixing Lambda bugs without redeploying the state machine
- This violates `AwsSolutions-IAM5` — suppress with justification:

```typescript
NagSuppressions.addResourceSuppressions(
  stateMachine,
  [
    {
      id: 'AwsSolutions-IAM5',
      reason:
        'We invoke $LATEST to allow redrives after Lambda bug fixes without redeploying the state machine',
    },
  ],
  true
);
```

### Implementation

In the CDK step-functions builder, use `latestVersion.functionArn` for substitutions:

```typescript
definitionSubstitutions[sfnSubstitutionKey] = lambdaObject.lambdaFunction.latestVersion.functionArn;
```

## State Machine Architecture

All pipeline managers follow the same core state machines, with downstream services adding a fifth:

| State Machine                       | Purpose                                                                                                                     |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `populateDraftData`                 | Resolves defaults, populates missing fields from upstream services                                                          |
| `validateDraftDataAndPutReadyEvent` | JSON schema + business-rule validation, then emits READY                                                                    |
| `readyEventToIcav2WesRequestEvent`  | Converts READY payload to ICAv2 WES request format                                                                          |
| `icav2WesEventToWrscEvent`          | Converts ICAv2 state changes to WorkflowRunUpdate events                                                                    |
| `glueSucceededEventsToDraftUpdate`  | _(Downstream only)_ Reacts to upstream SUCCEEDED events, finds matching DRAFT runs, and updates them with new upstream data |

### Naming

State machine logical names use camelCase in TypeScript. The CDK builder converts them to snake_case for the ASL template filename:

```
populateDraftData → populate_draft_data_sfn_template.asl.json
```

The deployed AWS resource name uses the double-hyphen convention:

```
orca-<workflow-name>--populateDraftData
```

## Error Handling

- On validation failure: write a comment to the workflow run record via `add_comment_to_workflow_run`, then exit silently (do not throw)
- On ICAv2 submission failure: the `addWesFailureComment` Lambda writes a failure comment before emitting the WRSC event
- Use Step Functions native retry/catch blocks for transient errors (API throttling, timeouts)

## Find Latest Workflow Lambda

The `findLatestWorkflow` Lambda is used by downstream pipeline managers to query the Workflow Manager API for existing workflow runs matching given criteria. It is critical for both:

- **`glueSucceededEventsToDraftUpdate`**: Finding existing DRAFT runs for this service to update when upstream workflows succeed
- **`populateDraftData`**: Finding upstream SUCCEEDED workflows to collect their outputs as inputs

### Input Parameters

| Parameter         | Required    | Description                                                                                  |
| ----------------- | ----------- | -------------------------------------------------------------------------------------------- |
| `workflowName`    | Yes         | The workflow name to search for                                                              |
| `workflowVersion` | No          | Filter to a specific workflow version                                                        |
| `status`          | No          | Filter to a specific workflow status (e.g. `DRAFT`, `SUCCEEDED`)                             |
| `libraries`       | Conditional | List of library objects (each with `libraryId`). Required if `analysisRunId` is not provided |
| `analysisRunId`   | Conditional | OrcaBus analysis run ID. Required if `libraries` is not provided                             |
| `rgidList`        | No          | List of RGID strings for finer-grained matching                                              |

### DRAFT Deduplication Logic

When `status` is `SUCCEEDED` and multiple workflow runs are found, the Lambda must check whether a more recent run (by `currentState.orcabusId`) exists that is still in-progress (neither SUCCEEDED nor in a terminated state like FAILED/ABORTED/RESOLVED). If such a run exists, return an empty list — the newer run supersedes the succeeded one and should be awaited.

### Matching Libraries Includes DRAFT Runs

When searching for workflow runs, the `findLatestWorkflow` Lambda must ensure that **DRAFT workflow runs with matching libraries are included in the query results**. This is essential because:

1. **Upstream glue pattern**: When an upstream pipeline succeeds, the downstream service's `glueSucceededEventsToDraftUpdate` state machine calls `findLatestWorkflow` with `status=DRAFT` to find its own DRAFT runs that need updating. The query must match on libraries (or analysisRunId + rgidList) to find the correct DRAFT workflows.

2. **Preventing duplicate drafts**: Before creating a new DRAFT, services should check whether a DRAFT already exists for the same set of libraries. The `findLatestWorkflow` result is used to determine whether to update an existing DRAFT or skip creation.

3. **Library-based matching**: The `library_id_list` parameter passed to `get_workflow_runs_from_metadata` must include all library IDs from the `libraries` input. This ensures DRAFT runs that were created for the same library set are found, even if they haven't progressed beyond DRAFT status yet.

### Implementation Notes

- Uses `orcabus_api_tools.workflow.get_workflow_runs_from_metadata` to query the Workflow Manager API
- Results are sorted by `orcabusId` descending (most recent first)
- Returns `{"workflowRunList": [...]}` or `{"workflowRunList": []}` if no match
- The Lambda requires the `needsOrcabusApiTools` IAM requirement flag

### Glue Succeeded Events Pattern

The `glueSucceededEventsToDraftUpdate` state machine follows this flow:

```
1. Receive upstream SUCCEEDED event (portalRunId, libraries, workflow info)
2. Get the upstream workflow run object
3. Call findLatestWorkflow with status=DRAFT for THIS service's workflow name
   → Must match on libraries (and rgidList if available) to find the correct DRAFT runs
4. For each found DRAFT portal run ID:
   a. Get the DRAFT payload
   b. Get upstream workflow outputs (e.g. alignment data from the succeeded run)
   c. Merge upstream outputs into the DRAFT payload
   d. Compare old vs new payload
   e. If changed → emit WorkflowRunUpdate DRAFT event with the merged payload
5. If no DRAFT runs found → exit silently (the glue event arrived before the DRAFT was created)
```

This pattern ensures that when upstream data becomes available, any existing downstream DRAFT workflows are automatically updated with the new inputs — without requiring a full re-trigger of the draft creation flow.
