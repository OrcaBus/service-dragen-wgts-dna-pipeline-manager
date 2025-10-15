#!/usr/bin/env python3

"""
Add the post analysis tags

Given the inputs;
dragenSomaticVariantCallingSampleName
dragenSomaticVariantCallingOutputUri and
dragenGermlineVariantCallingSampleName
dragenGermlineVariantCallingOutputUri

Perform the following:

For each directory collect the following metrics:
* hrdscore (if available - tumor only)
* tmb-metrics (if available - tumor only)
* SV PASS (if available - tumor only)
* CNV Estimated Tumor Purity (tumor only)
* CNV Overall Ploidy (tumor only)
* Average autosomal coverage over genome
* Contamination Rate
* Duplication Rate
* total Variants
* tiTvRatio

"""

# Standard imports
from typing import Optional
from io import StringIO
import pandas as pd
import requests
import json

# Layer imports
from orcabus_api_tools.filemanager import get_presigned_url, get_file_object_from_s3_uri
from orcabus_api_tools.filemanager.errors import S3FileNotFoundError

# Globals
FILENAME_BY_METRIC = {
    "HRD_SCORE": "{SAMPLE_NAME}.hrdscore.csv",
    "TMB_METRICS": "{SAMPLE_NAME}.tmb.metrics.csv",
    "SV_METRICS": "{SAMPLE_NAME}.sv_metrics.csv",
    "CNV_METRICS": "{SAMPLE_NAME}.cnv_metrics.csv",
    "TUMOR_MAPPING_METRICS": "{SAMPLE_NAME}.wgs_coverage_metrics_tumor.csv",
    "MAPPING_METRICS": "{SAMPLE_NAME}.wgs_coverage_metrics.csv",
    "METRICS_JSON": "{SAMPLE_NAME}.metrics.json",
}

def read_file_from_s3(uri: str) -> Optional[str]:

    try:
        file_obj = get_file_object_from_s3_uri(uri)
    except S3FileNotFoundError as e:
        return None

    return requests.get(get_presigned_url(file_obj['s3ObjectId'])).text


def read_csv_from_s3(
        uri: str,
        **kwargs
) -> Optional[pd.DataFrame]:

    csv_content = read_file_from_s3(uri)

    if csv_content is None:
        return None

    return pd.read_csv(
        StringIO(csv_content),
        **kwargs,
    )


def read_json_from_s3(
        uri: str,
        **kwargs
) -> Optional[dict]:

    json_content = read_file_from_s3(uri)

    if json_content is None:
        return None

    return json.loads(json_content)


def get_hrd_score(
        output_uri: str,
        sample_name: str
) -> Optional[int]:
    """
    HRD DF looks like this:
    Sample,LOH_Score,TAI_Score,LST_Score,HRD_Score
    L2300902,18,27,34,79
    """
    hrd_score_file_name = FILENAME_BY_METRIC["HRD_SCORE"].format(
        SAMPLE_NAME=sample_name,
    )
    hrd_score_df = read_csv_from_s3(f"{output_uri}{hrd_score_file_name}")

    if hrd_score_df is None or hrd_score_df.empty:
        return -1

    return hrd_score_df.query("Sample == @sample_name")["HRD_Score"].item()


def get_tmb_score(
        output_uri: str,
        sample_name: str
) -> Optional[int]:
    """
    TMB DF looks like this:
    Sample,TMB,Callable_Bases,Mutations,Panel_Size
    L2300902,8.5,944000000,8,944000000
    """
    tmb_metrics_file_name = FILENAME_BY_METRIC["TMB_METRICS"].format(
        SAMPLE_NAME=sample_name
    )
    tmb_metrics_df = read_csv_from_s3(
        f"{output_uri}{tmb_metrics_file_name}",
        header=None,
        names=[
            "summary", "null", "metric", "value"
        ]
    )

    if tmb_metrics_df is None or tmb_metrics_df.empty:
        return -1

    return tmb_metrics_df.query("metric == 'TMB'")["value"].item()


def get_sv_pass_count(
        output_uri: str,
        sample_name: str,
) -> Optional[int]:
    """
    SV SUMMARY,L2300902/L2300901,Total number of structural variants (PASS),753
    SV SUMMARY,L2300902/L2300901,Number of deletions (PASS),511,67.86
    SV SUMMARY,L2300902/L2300901,Number of insertions (PASS),71,9.43
    SV SUMMARY,L2300902/L2300901,Number of duplications (PASS),51,6.77
    SV SUMMARY,L2300902/L2300901,Number of breakend pairs (PASS),120,15.94
    """
    sv_metrics_file_name = FILENAME_BY_METRIC["SV_METRICS"].format(
        SAMPLE_NAME=sample_name
    )
    sv_metrics_df = read_csv_from_s3(
        f"{output_uri}{sv_metrics_file_name}",
        header=None,
        names=[
            "summary", "sample", "metric", "value", "pct"
        ],
    )

    if sv_metrics_df is None or sv_metrics_df.empty:
        return -1


    return sv_metrics_df.query("metric == 'Total number of structural variants (PASS)'")["value"].item()


def get_cnv_estimated_tumor_purity(
        output_uri: str,
        sample_name: str,
) -> Optional[float]:
    """
    CNV SUMMARY,,Bases in reference genome,3217346917
    CNV SUMMARY,,Average alignment coverage over genome,74.43
    CNV SUMMARY,,Number of alignment records,2009441813
    CNV SUMMARY,,Number of filtered records (total),409892023,20.40
    CNV SUMMARY,,Number of filtered records (duplicates),289145549,14.39
    CNV SUMMARY,,Number of filtered records (MAPQ),92253320,4.59
    CNV SUMMARY,,Number of filtered records (unmapped),39463101,1.96
    CNV SUMMARY,,PMAD,0.101298
    CNV SUMMARY,,OutlierBafFraction,0.004856
    CNV SUMMARY,,Number of target intervals,2441305
    CNV SUMMARY,,Number of segments,695
    CNV SUMMARY,,Number of amplifications,94
    CNV SUMMARY,,Number of deletions,118
    CNV SUMMARY,,Number of passing amplifications,79,84.04
    CNV SUMMARY,,Number of passing deletions,70,59.32
    CNV SUMMARY,,Estimated tumor purity,0.60
    CNV SUMMARY,,Diploid coverage,278.00
    CNV SUMMARY,,Overall ploidy,2.06
    CNV SUMMARY,,Homozygosity index,0.091
    """
    cnv_metrics_file_name = FILENAME_BY_METRIC["CNV_METRICS"].format(
        SAMPLE_NAME=sample_name
    )
    cnv_metrics_df = read_csv_from_s3(
        f"{output_uri}{cnv_metrics_file_name}",
        header=None,
        names=[
            "summary", "sample", "metric", "value", "pct"
        ],
    )

    if cnv_metrics_df is None or cnv_metrics_df.empty:
        return -1

    return round(
        cnv_metrics_df.query("metric == 'Estimated tumor purity'")["value"].item(),
        4
    )


def get_cnv_overall_ploidy(
        output_uri: str,
        sample_name: str,
) -> Optional[float]:
    """
    CNV SUMMARY,,Bases in reference genome,3217346917
    CNV SUMMARY,,Average alignment coverage over genome,74.43
    CNV SUMMARY,,Number of alignment records,2009441813
    CNV SUMMARY,,Number of filtered records (total),409892023,20.40
    CNV SUMMARY,,Number of filtered records (duplicates),289145549,14.39
    CNV SUMMARY,,Number of filtered records (MAPQ),92253320,4.59
    CNV SUMMARY,,Number of filtered records (unmapped),39463101,1.96
    CNV SUMMARY,,PMAD,0.101298
    CNV SUMMARY,,OutlierBafFraction,0.004856
    CNV SUMMARY,,Number of target intervals,2441305
    CNV SUMMARY,,Number of segments,695
    CNV SUMMARY,,Number of amplifications,94
    CNV SUMMARY,,Number of deletions,118
    CNV SUMMARY,,Number of passing amplifications,79,84.04
    CNV SUMMARY,,Number of passing deletions,70,59.32
    CNV SUMMARY,,Estimated tumor purity,0.60
    CNV SUMMARY,,Diploid coverage,278.00
    CNV SUMMARY,,Overall ploidy,2.06
    CNV SUMMARY,,Homozygosity index,0.091
    """
    cnv_metrics_file_name = FILENAME_BY_METRIC["CNV_METRICS"].format(
        SAMPLE_NAME=sample_name
    )
    cnv_metrics_df = read_csv_from_s3(
        f"{output_uri}{cnv_metrics_file_name}",
        header=None,
        names=[
            "summary", "sample", "metric", "value", "pct"
        ],
    )

    if cnv_metrics_df is None or cnv_metrics_df.empty:
        return -1

    return round(
        cnv_metrics_df.query("metric == 'Overall ploidy'")["value"].item(),
        4
    )


def get_avg_cov_over_genome(
        output_uri: str,
        sample_name: str,
        is_tumor: bool = False
) -> Optional[float]:
    """
    COVERAGE SUMMARY,,Aligned bases,239749015107
    COVERAGE SUMMARY,,Aligned bases in genome,239749015107,100.00
    COVERAGE SUMMARY,,Average alignment coverage over genome,79.31
    COVERAGE SUMMARY,,Uniformity of coverage (PCT > 0.2*mean) over genome,93.95
    COVERAGE SUMMARY,,Uniformity of coverage (PCT > 0.4*mean) over genome,93.05
    COVERAGE SUMMARY,,PCT of genome with coverage [1500x: inf),0.01
    COVERAGE SUMMARY,,PCT of genome with coverage [1000x: inf),0.01
    COVERAGE SUMMARY,,PCT of genome with coverage [ 500x: inf),0.02
    COVERAGE SUMMARY,,PCT of genome with coverage [ 100x: inf),17.62
    COVERAGE SUMMARY,,PCT of genome with coverage [  50x: inf),88.64
    COVERAGE SUMMARY,,PCT of genome with coverage [  20x: inf),93.75
    COVERAGE SUMMARY,,PCT of genome with coverage [  15x: inf),94.01
    COVERAGE SUMMARY,,PCT of genome with coverage [  10x: inf),94.30
    COVERAGE SUMMARY,,PCT of genome with coverage [   3x: inf),94.95
    COVERAGE SUMMARY,,PCT of genome with coverage [   1x: inf),95.41
    COVERAGE SUMMARY,,PCT of genome with coverage [   0x: inf),100.00
    COVERAGE SUMMARY,,PCT of genome with coverage [1000x:1500x),0.00
    COVERAGE SUMMARY,,PCT of genome with coverage [ 500x:1000x),0.01
    COVERAGE SUMMARY,,PCT of genome with coverage [ 100x: 500x),17.60
    COVERAGE SUMMARY,,PCT of genome with coverage [  50x: 100x),71.02
    COVERAGE SUMMARY,,PCT of genome with coverage [  20x:  50x),5.11
    COVERAGE SUMMARY,,PCT of genome with coverage [  15x:  20x),0.25
    COVERAGE SUMMARY,,PCT of genome with coverage [  10x:  15x),0.29
    COVERAGE SUMMARY,,PCT of genome with coverage [   3x:  10x),0.65
    COVERAGE SUMMARY,,PCT of genome with coverage [   1x:   3x),0.46
    COVERAGE SUMMARY,,PCT of genome with coverage [   0x:   1x),4.59
    COVERAGE SUMMARY,,Median chr X coverage (ignore 0x regions) over genome,85.00
    COVERAGE SUMMARY,,Median chr Y coverage (ignore 0x regions) over genome,2.00
    COVERAGE SUMMARY,,Average mitochondrial coverage over genome,17866.66
    COVERAGE SUMMARY,,Average autosomal coverage over genome,82.16
    COVERAGE SUMMARY,,Median autosomal coverage over genome,83.00
    COVERAGE SUMMARY,,Mean/Median autosomal coverage ratio over genome,0.99
    COVERAGE SUMMARY,,Aligned reads,1601182730
    COVERAGE SUMMARY,,Aligned reads in genome,1601182730,100.00
    """
    if is_tumor:
        mapping_metrics_file_name = FILENAME_BY_METRIC["TUMOR_MAPPING_METRICS"].format(
            SAMPLE_NAME=sample_name
        )
    else:
        mapping_metrics_file_name = FILENAME_BY_METRIC["MAPPING_METRICS"].format(
            SAMPLE_NAME=sample_name
        )
    mapping_metrics_df = read_csv_from_s3(
        f"{output_uri}{mapping_metrics_file_name}",
        header=None,
        names=[
            "summary", "region", "metric", "value", "pct"
        ],
    )

    if mapping_metrics_df is None or mapping_metrics_df.empty:
        return -1

    return round(
        mapping_metrics_df.query("metric == 'Average autosomal coverage over genome'")["value"].item(),
        4
    )


def get_contamination_rate(
        output_uri: str,
        sample_name: str,
) -> Optional[float]:
    """
    Get the contamination rate from the metrics.json file
    """
    metrics_file_name = FILENAME_BY_METRIC["METRICS_JSON"].format(
        SAMPLE_NAME=sample_name
    )

    # Read metrics json
    metrics_json = read_json_from_s3(f"{output_uri}{metrics_file_name}")

    if metrics_json is None:
        return None

    return round(
        metrics_json.get("modules", {}).get("mapAlign", {}).get("globalMetrics", {}).get("estimatedSampleContamination", {}).get("value"),
        4
    )


def get_duplication_rate(
        output_uri: str,
        sample_name: str,
) -> Optional[float]:
    """
    Get the duplication rate from the metrics.json file
    """
    metrics_file_name = FILENAME_BY_METRIC["METRICS_JSON"].format(
        SAMPLE_NAME=sample_name
    )

    metrics_json = read_json_from_s3(f"{output_uri}{metrics_file_name}")

    if metrics_json is None:
        return None

    return round(
        metrics_json.get("modules", {}).get("mapAlign", {}).get("globalMetrics", {}).get("duplicateMarkedReads", {}).get("percentage") / 100,
        4
    )


def get_total_variants(
        output_uri: str,
        sample_name: str,
) -> Optional[int]:
    """
    Get the total variants from the metrics.json file
    """
    metrics_file_name = FILENAME_BY_METRIC["METRICS_JSON"].format(
        SAMPLE_NAME=sample_name
    )

    metrics_json = read_json_from_s3(f"{output_uri}{metrics_file_name}")

    if metrics_json is None:
        return None

    return metrics_json.get("modules", {}).get("variantCaller", {}).get("postFilter", {}).get(sample_name, {}).get("totalVariants", {}).get("value")


def get_ti_tv_ratio(
        output_uri: str,
        sample_name: str,
) -> Optional[float]:
    """
    Get the ti/tv ratio from the metrics.json file
    """
    metrics_file_name = FILENAME_BY_METRIC["METRICS_JSON"].format(
        SAMPLE_NAME=sample_name
    )

    metrics_json = read_json_from_s3(f"{output_uri}{metrics_file_name}")

    if metrics_json is None:
        return None

    return round(
        metrics_json.get("modules", {}).get("variantCaller", {}).get("postFilter", {}).get(sample_name, {}).get("tiTvRatio", {}).get("value"),
        4
    )


def snake_to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def handler(event, context):
    """
    Add the post analysis tags to the event
    """

    # Get the inputs
    sample_name = event.get("variantCallingSampleName")
    output_uri = event.get("variantCallingOutputUri")
    is_tumor = event.get("isTumor", False)

    if not sample_name or not output_uri:
        raise ValueError("Missing required inputs")

    tags = {}

    # Get the metrics
    if is_tumor:
        tags["hrd_score"] = get_hrd_score(output_uri, sample_name)
        tags["tmb_score"] = get_tmb_score(output_uri, sample_name)
        tags["sv_pass_count"] = get_sv_pass_count(output_uri, sample_name)
        tags["cnv_estimated_tumor_purity"] = get_cnv_estimated_tumor_purity(output_uri, sample_name)
        tags["cnv_overall_ploidy"] = get_cnv_overall_ploidy(output_uri, sample_name)
        tags["avg_autosomal_coverage_over_genome"] = get_avg_cov_over_genome(output_uri, sample_name, is_tumor=True)
    else:
        tags["avg_autosomal_coverage_over_genome"] = get_avg_cov_over_genome(output_uri, sample_name, is_tumor=False)

    tags["contamination_rate"] = get_contamination_rate(output_uri, sample_name)
    tags["duplication_frac"] = get_duplication_rate(output_uri, sample_name)
    tags["total_post_filter_variants"] = get_total_variants(output_uri, sample_name)
    tags["ti_tv_ratio"] = get_ti_tv_ratio(output_uri, sample_name)

    if is_tumor:
        # Prepend 'tumor_' to the keys
        tags = dict(map(
            lambda item: (f"tumor_{item[0]}", item[1]),
            tags.items()
        ))

    # Now convert the keys to camelCase
    tags = dict(map(
        lambda item: (snake_to_camel(item[0]), item[1]),
        tags.items()
    ))

    # Return the tags
    return {
        "tags": tags
    }


# if __name__ == "__main__":
#     import json
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "variantCallingSampleName": "L2300902",
#                 "variantCallingOutputUri": "s3://project-data-889522050439-ap-southeast-2/byob-icav2/project-wgs-accreditation/analysis/dragen-wgts-dna/202509114694b95e/L2300902__L2300901__hg38__linear__dragen_wgts_dna_somatic_variant_calling/",
#                 "isTumor": True
#             },
#             None
#         ),
#         indent=4
#     ))
