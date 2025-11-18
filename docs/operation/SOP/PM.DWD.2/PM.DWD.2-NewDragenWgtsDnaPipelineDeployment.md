# New Dragen WGTS DNA Pipeline Deployment

- Version: 1.0
- Contact: Alexis Lucattini, [alexisl@unimelb.edu.au](mailto:alexisl@unimelb.edu.au)


There may be times where we need to create a new CWL workflow for our Dragen WGTS DNA pipeline.

In the SOP below we discuss the following scenarios:
* User wants to tinker with some parameters in the current CWL workflow for testing purposes only.
* User wants to add a new feature to the pipeline that requires a modification to the current CWL workflow.
* User wants to make a new release of the edited CWL workflow for production use.

Throughout the SOP we make the following expectations:
* User is familiar with UMCCR's [cwl-ica repository][cwl_ica_repo] and has a working knowledge of CWL.
* User has access to the ICAv2 platform with at minimum 'Contributor level' permissions in at least one project.
* User has access to the appropriate AWS Account tied to the ICAv2 project.


- [Pipeline Summary](#pipeline-summary)
- [Setup](#setup)
  - [Installing CWL-ICA-CLI](#installing-cwl-ica-cli)
  - [Installing ICAv2 CLI and ICAv2 CLI Plugins](#installing-icav2-cli-and-icav2-cli-plugins)
- [Development Deployment](#development-deployment)
  - [CWL ZIP](#cwl-zip)
  - [Pipeline Creation](#pipeline-creation)
  - [Running the Pipeline](#running-the-pipeline)
  - [Pipeline Update](#pipeline-update)
- [Production Deployment](#production-deployment)
  - [GitHub Releases](#github-releases)
  - [Infrastructure Constants Updates](#infrastructure-constants-updates)
  - [Workflow Manager Updates](#workflow-manager-updates)
  - [Analysis Glue Updates](#analysis-glue-updates)


## Pipeline Summary

The pipeline runs on [ICA][ica_about], using [CWL][cwl_user_guide] (Common Workflow Language) as the workflow orchestration language
to drive the pipeline. The CWL Workflow for Dragen WGTS DNA is located in our [cwl-ica][cwl_ica_repo] repository.
And follows a 'release-based' auto-deployment into ICA for production use.

The Dragen WGTS DNA pipeline has the following major steps:

1. Somatic Alignment and Variant Calling
2. Germline Alignment and Variant Calling
3. Quality Control and Reporting via MultiQC

Rather than providing command-line arguments to Dragen, the pipeline generates a config file that is passed to DRAGEN with the `--config` argument.
This config file is also provided as an output for the user to easily confirm if the correct parameters were used.

We also support the following DRAGEN modules:

- Custom QC Coverage reports.
- Targeted Calling (germline only)
- Contamination Detection
- CNV Calling (somatic only)
- HRD Detection (somatic only)
- SV Calling (somatic only)
- MSI (Microsatellite instability) Detection (somatic only)
- TMB (Tumor Mutational Burden) Calculation (somatic only)

Outputs:

There are three main output directories from the pipeline:

* Somatic Output (<T_LIBID>__<N_LIBID>__hg38__linear__dragen_wgts_dna_somatic_variant_calling)
* Germline Output (<LIBID>__hg38__graph__dragen_wgts_dna_germline_variant_calling)
* MultiQC Report (<T_LIBID>__<N_LIBID>__multiqc)

## Setup

### Installing CWL-ICA-CLI

Follow the instructions in the [cwl-ica-wiki][cwl_ica_installation_link].

### Installing ICAv2 CLI and ICAv2 CLI Plugins

Download and install the latest version of the ICAv2 CLI from the [ICAv2 CLI Releases page][icav2_releases_page].

Then also install the ICAv2 CLI Plugins from the [ICAv2 CLI Plugins installation page][icav2_plugins_installation_page].

## Development Deployment

For deployment into the development environment, we follow the very important philosophy of "this probably isn't going to work the first time",
and as such we want to be able to tinker with any workflow we create on the ICAv2 platform without having to create a new release every time we want to test something.

Fortunately ICAv2 supports pipelines in 'DRAFT' mode which can be edited at any time.
This allows us to tinker with parameters and test new features without having to create a new release every time.

The steps below outline how to deploy a new or modified CWL workflow into the development environment.

### CWL ZIP

The CWL workflow needs to be packaged into a ZIP file for deployment into ICA. While ICA supports 'packed' CWL workflows,
these are particularly difficult to read and edit, and as such we prefer to use the ZIP format that then creates a directory structure in ICA that is easy to navigate.

To create a ZIP file of the CWL workflow, we use the `cwl-ica` CLI tool that we installed earlier and run the following command

```shell
cwl-ica icav2-zip-workflow \
  --workflow-path workflows/dragen-wgts-dna-pipeline/4.4.4/dragen-wgts-dna-pipeline__4.4.4.cwl \  # Relative path to the cwl-ica repo root
  --force # Overwrite any existing ZIP file
```

This will output a ZIP file in the current working directory with the name `dragen-wgts-dna-pipeline__4.4.4.zip`

### Pipeline Creation

Once we have the ZIP file, we can then deploy it into ICAv2, keep note of the pipeline id, we will need it later
when we inevitably want to update the pipeline again. We should also ensure we're in the correct ICAv2 project

Enter the appropriate project

```shell
icav2 projects enter development
```

Create the pipeline

```shell
icav2 projectpipelines create-cwl-pipeline-from-zip \
  dragen-wgts-dna-pipeline__4.4.4.zip
```

Keep note of the pipeline ID outputted from the command above.

### Running the Pipeline

Once the pipeline is created, we can then run it on a test dataset to ensure that it works as expected.
See [SOP 1][sop_1_rel_path] for instructions on how to kick off the pipeline.

Note you will need to manually add in the following into the payload section of the WorkflowRunUpdate event.

```json5
{
  // ... Other top level items such as portal run id
  "payload": {
    "version": "<DEFAULT_PAYLOAD_VERSION>", // Must be set to 2025.06.04
    "data": {
      "engineParameters": {
        "pipelineId": "<THE PIPELINE ID YOU JUST CREATED>"
      }
    }
  }
}
```

The workflow can then be monitored via the [OrcaBus Dev UI interface][orcabus_dev_ui_link].

### Pipeline Update

Did your pipeline not work? Well aren't you glad you deployed it in DRAFT mode / development first?

Fortunately, once we fix what went wrong, we can easily repeat the step above and try again.

Step 1: Update the CWL code, and do it properly this time (not like the last time that was an epic fail!)
Step 2: Zip up the CWL code again using the `cwl-ica icav2-zip-workflow` command above.
Step 3: Update the pipeline in ICAv2 using the following command (where <pipeline_id> is the ID you kept note of earlier)
  ```
  icav2 projectpipelines update dragen-wgts-dna-pipeline__4.4.4.zip <pipeline_id>
  ```
Step 4: Rerun the pipeline using the same steps as above.


## Production Deployment

Okay, so you've got your pipeline working in development, and now you want to make it available for production use.

We now need to do the following steps in order for our workflow to be up and running in our production environment:

1. Make a CWL-ICA GitHub release
2. Update the [infrastructure constants in this repository][infrastructure_constants_rel_path]
3. Run the make-new-workflow.sh command under [scripts in this repository][scripts_rel_path]
4. Update the constants in the [analysis-glue repository][analysis_glue_repo_link]

### GitHub Releases

We first push our new cwl-ica code to a branch, have it reviewed and approved via a pull request, and then merge it into the main branch.

Make sure your local repo is up to date and on the main branch

```shell
git checkout main
git pull origin main
```

Now it's time to create a new release!

```shell
cwl-ica workflow-release \
  --workflow-path workflows/dragen-wgts-dna-pipeline/4.4.4/dragen-wgts-dna-pipeline__4.4.4.cwl
```

This will take about ten minutes to complete, but you should now see your new release in the [GitHub Releases page][cwl_ica_releases_page].

### Infrastructure Constants Updates

While this updates an SSM parameter that isn't explicity used anywhere right now, it's good practice to keep this updated for future reference,
and helps the next developer out when they're trying to figure out what the latest version is.

You should be able to find the snippet to replace as something that looks like this:

```typescript
export const WORKFLOW_VERSION_TO_DEFAULT_ICAV2_PIPELINE_ID_MAP: Record<
  WorkflowVersionType,
  string
> = {
  // PATH_TO_RELEASE
  '4.4.4': '<THE PIPELINE ID YOU KEPT NOTE OF EARLIER>',
};
```

Make sure to then make a PR and get it reviewed and approved before merging it into main.
This will then trigger CodePipeline to deploy the changes to the appropriate AWS Accounts.

### Workflow Manager Updates

We also need to register the workflow with the [Workflow Manager][workflow_manager_repo_link].

We can perform the following command to register the new workflow version:

```shell
make-new-workflow.sh \
  --workflow-name 'dragen-wgts-dna' \
  --workflow-version "4.4.4" \
  --executionEngine "ICA" \
  --executionEnginePipelineId "<THE PIPELINE ID YOU KEPT NOTE OF EARLIER>" \
  --codeVersion "$(cd <cwl-ica-repo> && git rev-parse --short=7 HEAD)" \
  --validationState "VALIDATED"
```

Make note of the new orcabus ID.


### Analysis Glue Updates

Head to the [analysis-glue repository][analysis_glue_repo_link] and update the constants in the `infrastructure/stage/constants.ts` file to include
the new workflow. You will not need to add in the workflow orcabus id, but all the other attributes used to create the workflow object
will be required.

You should be able to find the snippet to replace as something that looks like this:

```typescript
export const WORKFLOW_VERSIONS_BY_NAME: Record<StageName, WorkflowObjectType> = {
  PROD: {
    // ... Other pipelines
    dragenWgtsDna: {
      orcabusId: '<NEW ORCABUS ID>',
      version: '4.4.4',
    }
  }
}
```


[ica_about]: https://www.illumina.com/products/by-type/informatics-products/connected-analytics.html
[cwl_user_guide]: https://www.commonwl.org/user_guide/
[cwl_ica_repo]: https://github.com/umccr/cwl-ica
[cwl_ica_installation_link]: https://github.com/umccr/cwl-ica/wiki/Getting_Started#installation
[icav2_releases_page]: https://help.ica.illumina.com/command-line-interface/cli-installation
[icav2_plugins_installation_page]: https://github.com/umccr/icav2-cli-plugins/wiki#installation
[sop_1_rel_path]: ../PM.DWD.1/PM.DWD.1-ManualPipelineExecution.md
[orcabus_dev_ui_link]: https://orcaui.dev.umccr.org/
[analysis_glue_repo_link]: https://github.com/OrcaBus/service-analysis-glue
[scripts_rel_path]: ../../../../scripts
[infrastructure_constants_rel_path]: ../../../../infrastructure/constants.ts
[cwl_ica_releases_page]: https://github.com/umccr/cwl-ica
[workflow_manager_repo_link]: https://github.com/OrcaBus/service-workflow-manager
