# Updating Pipeline Parameters

From time-to-time there may be a requirement to add or subtract pipeline parameters.

Unfortunately, the DRAFT payload inputs we supply do not directly map to the pipeline parameters used when running ICAv2.
This is a little annoying but also improves the user experience as is allows us to provide more user-friendly names for input parameters.
This assumes that the [CWL pipeline][cwl-pipeline] has already been updated to support the new parameters. See [New Dragen WGTS DNA Deployment SOP][new_dragen_wgts_dna_deployment_sop] for more information.

## Constants File Update

To update any of our pipeline parameters, head to the infrastructure stage constants path and you should find something like the following.

<details>

<summary>Click to expand</summary>

```typescript
export const DEFAULT_WORKFLOW_INPUTS_BY_VERSION_MAP: Record<WorkflowVersionType, object> = {
  '4.4.4': {
    // Alignment options (both germline and somatic)
    alignmentOptions: {
      enableDuplicateMarking: true,
      qcCoverage: [
        // FCC Germline
        {
          name: 'fcc',
          region:
            's3://reference-data-503977275616-ap-southeast-2/refdata/gene-panels/v2--0/germline/umccr_predisposition_genes.transcript_regions.bed',
          reportType: 'cov_report',
        },
        // UMCCR Somatic
        {
          name: 'umccr',
          region:
            's3://reference-data-503977275616-ap-southeast-2/refdata/gene-panels/v2--0/somatic/umccr_cancer_genes.gene_regions.bed',
          reportType: 'cov_report',
        },
      ],
    },
    // Targeted caller options (germline only)
    targetedCallerOptions: {
      enableTargeted: ['cyp2d6'],
    },
    // SNV / MNV options (both germline and somatic)
    snvVariantCallerOptions: {
      // Contamination estimation
      qcDetectContamination: true,
      // Phased variants distance
      vcMnvEmitComponentCalls: true,
      vcCombinePhasedVariantsDistanceSnvsOnly: 2,
      vcCombinePhasedVariantsDistance: 2,
    },
    // CNV Options (somatic only)
    somaticCnvCallerOptions: {
      enableCnv: true,
      enableHrd: true,
      cnvUseSomaticVcBaf: true,
    },
    // SV Options (somatic only)
    somaticSvCallerOptions: {
      enableSv: true,
    },
    // MSI Options (somatic only) - Requires MSI reference file
    somaticMsiOptions: {
      msiCommand: 'tumor-normal',
      msiMicrosatellitesFile: MSI_REFERENCE_PATH_MAP['4.4.4'],
      // 40 suggested here - https://help.dragen.illumina.com/product-guide/dragen-v4.4/dragen-recipes/dna-somatic-tumor-normal-solid-wgs#msi
      msiCoverageThreshold: 40, // Default is 60 (allegedly) but it's not actually a default
    },
    // TMB Requires nirvana annotation data (somatic only)
    somaticNirvanaAnnotationOptions: {
      enableVariantAnnotation: true,
      variantAnnotationAssembly: 'GRCh38',
      // Not required but saves us having to do through the nirvana download step
      // Which can break without any error messages
      variantAnnotationData: VARIANT_ANNOTATION_DATA_PATH_MAP['4.4.4'],
    },
    // Also need to enable TMB
    somaticTmbOptions: {
      enableTmb: true,
    },
  },
}
```

</details>

Edit away!

## Draft Event Schema

If you are adding or removing parameters, you may need to update the [DRAFT event schema][draft_event_schema] to reflect these changes.
This ensures that the input validation for the DRAFT payload is accurate and up-to-date.

## Lambda Parameter Mapping

If you are adding or removing parameters, you will need to update the mapping logic in the [ready to icav2 wes request_lambda][ready_to_icav2_wes_request_lambda] to ensure that the
DRAFT payload inputs are correctly mapped to the ICAv2 pipeline parameters.

## Testing

Deploy your changes to development /#FIXME

As a first pass, you may wish to follow the [Manual Pipeline Execution SOP][manual_pipeline_execution_sop] to ensure
that the changes you have made are functioning as expected.

Once you are happy with the changes, you can trigger a full run through the [Pipeline Verification SOP][verification_testing_sop] to ensure that everything is working as expected.
