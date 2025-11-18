# Trouble Shooting

- Version: 1.0
- Contact: Alexis Lucattini, [alexisl@unimelb.edu.au](mailto:alexisl@unimelb.edu.au)


Most processes within the Dragen WGTS DNA Orchestration use AWS Step Functions to manage the workflow.
We post all Step Function errors to the #alerts-prod slack channel, a Center staff member can
then click on the offending Step Function link in the slack message to be taken to the AWS Step Functions console to investigate further.

- [Analysis Stuck in DRAFT state.](#analysis-stuck-in-draft-state)
  - [Fastq Sync Stuck](#fastq-sync-stuck)
  - [Payload Mismatch](#payload-mismatch)
- [Analysis Stuck in READY state](#analysis-stuck-in-ready-state)
- [Analysis Fails to Start](#analysis-fails-to-start)
  - [Project Not Set Up Correctly](#project-not-set-up-correctly)
  - [Invalid Pipeline ID](#invalid-pipeline-id)
  - [Data Not Available](#data-not-available)
- [Common Dragen Failures](#common-dragen-failures)
  - [Dragen Step Fails with a 137 Exit Code](#dragen-step-fails-with-a-137-exit-code)


## Analysis Stuck in DRAFT state.

If the analysis is stuck in DRAFT mode, there may be a couple of reasons for this.
To determine which issue is causing the problem we can head to the [AWS Step Functions Console][aws_step_functions_console_prod]
in the production account and look for any RUNNING executions in the 'dragen-wgts-dna--populate-draft-data' step function.

If there is a RUNNING execution for this library id, then the issue is likely due to the Step Functions hanging at the Fastq Sync step.
See the Fastq Sync stuck section below for more information for hanging processes.

If there is no RUNNING execution for this library id, then the issue is likely due to a payload being incomplete.
See the Payload Mismatch section below for more information on how to resolve this issue.

### Fastq Sync Stuck

The Fastq Sync step may hang for a number of hours. Reasons may include:

* Fastq QC stat jobs are taking a long time to complete (usually no longer than one hour)
* Fastq data is still being sequenced and is not yet available for processing (depends on sequencing run, usually up to 48 hours)
* Fastq data is being thawed from archive storage (S3 Glacier) (usually around 8 to 10 hours)

The fastq sync service will find fastq ids associated with running jobs, be it active sequencing runs, BCLConvert analyses, or unarchiving jobs.
Services using the Fastq Sync service will receive a heartbeat on their respective task token if any of their fastq ids have an active jobs.
If the step function is genuinely stuck, it will not receive any heartbeats and will therefore timeout after one hour.

The failed execution will push a message to the #alerts-prod slack channel.

You may wish to then 'redrive' the execution from the console.


### Payload Mismatch

> Note the below may soon be replaced with automated commentary on the OrcaUI for draft payloads that fail validation.

If you can find the most recent step function execution for this library id, then you may be able to look at the Log Group for the 'validate-draft-payload' lambda,
by clicking on the log group section for that particular lambda.

This lambda will let you know how the payload violates the expected schema.
You may wish to then manually update the payload and generate a new WorkflowRunUpdate draft event as discussed in [SOP 1][sop_1_rel_path].

## Analysis Stuck in READY state

If the analysis is stuck in READY state, then it is likely that the translation from the READY event to the ICAv2 WES event has failed.
This is a rare occurrence, but may be due to transient issues with the ICAv2 WES manager.
One can confirm that this has occurred by querying the offending workflow run name against the [ICAv2 WES Manager API][icav2_wes_api_swagger_page].
If no analysis is found for that workflow run name, then the issue is likely due to a communication failure between the Dragen WGTS DNA service
and the ICAv2 WES Manager.

## Analysis Fails to Start

The ICAv2 WES manager may fail to create an analysis for any of the following reasons:

### Project Not Set Up Correctly

This issue is mostly common with new projects often for research purposes that also use the OrcaBus system
to orchestrate the analyses.

Some common things to confirm can be:

* Ensure that the ICAv2 Production Service User has been added to the project with the correct permissions.
* Ensure that the Notifications Channels have been set up correctly for the project.

Please consult the [project setup SOP][icav2_wes_project_setup_sop] as part of the ICAv2 WES documentation

### Invalid Pipeline ID

> The pipeline id specified is not available in the project id

This can be mitigated with the following command from someone with ICAv2 access:

```
icav2 projects enter <project_id>
icav2 projectpipeline link <pipeline_id>
```

You will need to create a new workflow run after this change in order to reanalyse the library/libraries.

### Data Not Available

> Data .x. is not available in the project id <project_id>

If data is available via the S3 External Data Access Route from the ICAv2 WES manager, the WES manager will
use this route to access the data, which is the preferred method as it does not rely on data linking within ICAv2.

However, there may be times where this is not possible and the data needs to be linked within ICAv2.

The best possible solution would be to copy the data into the appropriate ICAv2 project and then
re-process the libraries to save the need of doing data linking within ICAv2.

If this is not possible, then you will need to link the data within ICAv2,
please consult the [ICAv2 Plugins Manual][icav2_wiki_page] for more information on how to do this.

## Common Dragen Failures

### Dragen Step Fails with a 137 Exit Code

This is likely due to insufficient memory. Structural Variant calling within Dragen is memory sensitive.
Unfortunately, there isn't much that can be done to mitigate this issue since we are restricted by the instance sizes.

It may be worth discussing with the project lead for this library to see if structural variant calling is required,
since we will also get the structural variants downstream through the ESVEE step of the oncoanalyser wgts dna pipeline.

It may also be worth checking the workflow type, (i.e clinical or research) and, if appropriate, re-running the pipeline through
dragen 4.4.6 which has a more memory efficient structural variant calling algorithm.

[aws_step_functions_console_prod]: https://472057503814.ap-southeast-2.console.aws.amazon.com/states/home?region=ap-southeast-2#/statemachines
[sop_1_rel_path]: ../PM.DWD.1/PM.DWD.1-ManualPipelineExecution.md
[icav2_wiki_page]: https://github.com/umccr/icav2-cli-plugins/wiki
[icav2_wes_project_setup_sop]: https://github.com/umccr/research-projects/tree/main/project-template/infrastructure
[icav2_wes_api_swagger_page]: https://icav2-wes.prod.umccr.org/schema/swagger-ui#/
