Manual Pipeline Execution
================================================================================
- Version: 1.0
- Contact: Alexis Lucattini, [alexisl@unimelb.edu.au](mailto:alexisl@unimelb.edu.au)


- [Introduction](#introduction)
- [Requirements](#requirements)
- [Procedure](#procedure)
- [Confirmation](#confirmation)


Introduction
--------------------------------------------------------------------------------

This Pipeline Manager manages the execution of the DRAGEN WGTS DNA pipeline. Here we describe the SOP for manual execution of the pipeline.

Requirements
--------------------------------------------------------------------------------

- appropriate AWS permissions
- AWS credentials set up in the local environment
- tools installed
  - AWS CLI
  - JQ

Procedure
--------------------------------------------------------------------------------

To initiate a pipeline execution we need to generate an initial DRAFT event. For more details consult the main [README](../../../../README.md).
For convenience, we provide a shell script that generates and optionally submits an appropriate event.

- familiarise yourself with the script: [generate-WRU-draft.sh](./generate-WRU-draft.sh)
  - especially check the settings in the `Globals` section
    - ensure the values are fit for your use case, e.g. for clinical samples match the accredited pipeline details
  - Set the engine parameters (if necessary) and library id(s) in the positional arguments.
- execute the script (e.g. `bash generate-WRU-draft.sh`)
  - Note: AWS credentials need to set on the environment
- the script should produce the JSON output of the DRAFT event that can be inspected to double check that reflects the intended request
  - take note of the generated `workflowRunName` or `portalRunId` and the URL to the OrcaBus Portal view of the workflow.


Confirmation
--------------------------------------------------------------------------------

The OrcaBus [Portal](https://portal.umccr.org/) can be used to check whether the event resulted in a WorkflowRun record.

- navigate to the Portal's WorkflowRun listing: https://portal.umccr.org/runs/workflow
- search for your WorkflowRun using the `workflowRunName` or `portalRunId`
- confirm that the WorkflowRun is listed and progressing as expected (check over time)
- once the WorkflowRun as `SUCCEEDED` the results should be available via the Portal's [Files](https://portal.umccr.org/files) view
  - simply filter by the `portalRunId`
