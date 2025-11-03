# Running Workflow Validation

For a quick workflow validation,
we use the HCC1395 cell line (L2300950 / L2300943) with the high-confidence truth set.

## Run Workflow

Follow steps in the [Manual Pipeline Execution SOP][manual_pipeline_execution_sop] to
run the workflow on the HCC1395 data.

## Validating the Results

Currently this is particularly challenging since we're using cell-lines rather than DNA
so we do expect some divergence from the truth set. This SOP is certainly a work-in-progress as
we determine ways to accurately set up sensitivity/specificity metrics.

We expect some differences between our variant calls and the truth set.

For now, we take a 95% SNV precision and recall as a passing metric for the workflow.

You can look at [example.sh](example.sh) for a full script.

### Setup: Define and pull Docker Images

We use the new seqera wave community docker images for this analysis.

```shell
# Docker images
SAMTOOLS_DOCKER_IMAGE="community.wave.seqera.io/library/samtools:1.22.1--eccb42ff8fb55509"
BCFTOOLS_DOCKER_IMAGE="community.wave.seqera.io/library/bcftools:1.22--a51ee80717c2467e"
HAP_PY_DOCKER_IMAGE="community.wave.seqera.io/library/hap.py:0.3.15--cc9c0286f5a6f629"
TABIX_DOCKER_IMAGE="community.wave.seqera.io/library/tabix:1.11--6c7fb31b37683708"

# Pull images
echo "$(date -Iseconds): Pulling docker images" 1>&2
docker pull "${SAMTOOLS_DOCKER_IMAGE}"
docker pull "${BCFTOOLS_DOCKER_IMAGE}"
docker pull "${HAP_PY_DOCKER_IMAGE}"
docker pull "${TABIX_DOCKER_IMAGE}"

````

### Step 1: Download the Truth Sets

```shell
# Downloads
HG38_REF_URI="https://s3.amazonaws.com/stratus-documentation-us-east-1-public/dragen/reference/Homo_sapiens/hg38.fa"

# Truth set
SNV_TRUTH_SET_URI="https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/release/latest/high-confidence_sSNV_in_HC_regions_v1.2.1.vcf.gz"
INDEX_TRUTH_SET_URI="https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/release/latest/high-confidence_sINDEL_in_HC_regions_v1.2.1.vcf.gz"
CALLING_BED_URI="https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/seqc/Somatic_Mutation_WG/release/latest/High-Confidence_Regions_v1.2.bed"

# Download reference
echo "$(date -Iseconds): Downloading reference" 1>&2
HG38_REF_PATH="$(basename "${HG38_REF_URI}")"
## REMOVE echo from wget to redownload file ##
echo wget \
  --output-document "${HG38_REF_PATH}" \
  "${HG38_REF_URI}"

echo "$(date -Iseconds): Indexing reference" 1>&2
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  "${SAMTOOLS_DOCKER_IMAGE}" \
	samtools faidx "/data/${HG38_REF_PATH}"

# Download truth sets
echo "$(date -Iseconds): Downloading truth sets" 1>&2
SNV_TRUTH_SET_PATH="$(basename "${SNV_TRUTH_SET_URI}")"
INDEL_TRUTH_SET_PATH="$(basename "${INDEX_TRUTH_SET_URI}")"
CALLING_BED_PATH="$(basename "${CALLING_BED_URI}")"

if [[ ! -f "${SNV_TRUTH_SET_PATH}" ]]; then
  echo "Downloading SNV truth set"
  wget \
    --output-document "${SNV_TRUTH_SET_PATH}" \
    "${SNV_TRUTH_SET_URI}"
fi

if [[ ! -f "${INDEL_TRUTH_SET_PATH}" ]]; then
  echo "Downloading INDEL truth set"
  wget \
    --output-document "${INDEL_TRUTH_SET_PATH}" \
    "${INDEX_TRUTH_SET_URI}"
fi

if [[ ! -f "${CALLING_BED_PATH}" ]]; then
  echo "Downloading Calling BED"
  wget \
    --output-document "${CALLING_BED_PATH}" \
    "${CALLING_BED_URI}"
fi

# Index truth sets
echo "$(date -Iseconds): Indexing truth sets" 1>&2
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  "${TABIX_DOCKER_IMAGE}" \
	tabix -p vcf "/data/${SNV_TRUTH_SET_PATH}"
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  "${TABIX_DOCKER_IMAGE}" \
	tabix -p vcf "/data/${INDEL_TRUTH_SET_PATH}"

```

### Step 2: Download and prepare the VCFs

```shell
# Dragen data
LIBRARY_ID_SOMATIC="L2300943"
LIBRARY_DATA_VCF_FILTERED="s3://test-data-503977275616-ap-southeast-2/testdata/analysis/production/dragen-wgts-dna/4.4.4/SEQC-II/01k3n0kn3nvsdtne265p0800qp/20250822e11a8540/L2300943__L2300950__hg38__linear__dragen_wgts_dna_somatic_variant_calling/L2300943.hard-filtered.vcf.gz"

# Download Dragen VCF
echo "$(date -Iseconds): Downloading Dragen VCF" 1>&2
DRAGEN_VCF_PATH="$(basename "${LIBRARY_DATA_VCF_FILTERED}")"
aws s3 cp "${LIBRARY_DATA_VCF_FILTERED}" "${DRAGEN_VCF_PATH}"
aws s3 cp "${LIBRARY_DATA_VCF_FILTERED}.tbi" "${DRAGEN_VCF_PATH}.tbi"

# Filter Dragen VCF to high confidence regions
echo "$(date -Iseconds): Filtering Dragen VCF to high confidence regions" 1>&2
FILTERED_SNPS_DRAGEN_VCF_PATH="${DRAGEN_VCF_PATH%.vcf.gz}.highconfbed.SNPs.vcf.gz"
FILTERED_INDELS_DRAGEN_VCF_PATH="${DRAGEN_VCF_PATH%.vcf.gz}.highconfbed.INDELs.vcf.gz"
# SNPs
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  "${BCFTOOLS_DOCKER_IMAGE}" \
    sh -c "
      bcftools view \
		--samples \"${LIBRARY_ID_SOMATIC}\" \
		--regions-file \"/data/${CALLING_BED_PATH}\" \
		\"/data/${DRAGEN_VCF_PATH}\" | \
	  bcftools view - \
		--types snps \
		--apply-filters PASS \
		--output-file \"/data/${FILTERED_SNPS_DRAGEN_VCF_PATH}\" \
		--write-index=tbi
    "
# INDELs
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  "${BCFTOOLS_DOCKER_IMAGE}" \
    sh -c "
      bcftools view \
		--samples \"${LIBRARY_ID_SOMATIC}\" \
		--regions-file \"/data/${CALLING_BED_PATH}\" \
		\"/data/${DRAGEN_VCF_PATH}\" | \
	  bcftools view - \
		--types indels \
		--apply-filters PASS \
		--output-file \"/data/${FILTERED_INDELS_DRAGEN_VCF_PATH}\" \
		--write-index=tbi
    "
```

### Step 3: Run som.py to compare VCFs

```shell

# Run som.py for SNPs
echo "$(date -Iseconds): Running som.py for SNPs" 1>&2
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  --env "HGREF=${HG38_REF_PATH}" \
  "${HAP_PY_DOCKER_IMAGE}" \
    som.py \
      --output som_py_snps_summary \
      "/data/${SNV_TRUTH_SET_PATH}" \
      "/data/${FILTERED_SNPS_DRAGEN_VCF_PATH}"

echo "$(date -Iseconds): Running som.py for INDELs" 1>&2
docker run \
  --user "$(id -u):$(id -g)" \
  --rm \
  --volume "${PWD}:/data" \
  --workdir /data \
  --env "HGREF=${HG38_REF_PATH}" \
  "${HAP_PY_DOCKER_IMAGE}" \
    som.py \
      --output som_py_snps_summary \
      "/data/${INDEL_TRUTH_SET_PATH}" \
      "/data/${FILTERED_INDELS_DRAGEN_VCF_PATH}"
```

### Validation Outputs

#### SNVS

```text
      type  total.truth  total.query     tp    fp    fn  unk  ambi    recall  recall_lower  recall_upper   recall2  precision  precision_lower  precision_upper   na  ambiguous  fp.region.size   fp.rate
1     SNVs        39447        34954  32949  2005  6498    0     0  0.835273      0.831588      0.838908  0.835273   0.942639         0.940164          0.94504  0.0        0.0      2875001522  0.697391
5  records        39447        34954  32949  2005  6498    0     0  0.835273      0.831588      0.838908  0.835273   0.942639         0.940164          0.94504  0.0        0.0      2875001522  0.697391
```

#### INDELS

```text
      type  total.truth  total.query    tp    fp   fn  unk  ambi    recall  recall_lower  recall_upper   recall2  precision  precision_lower  precision_upper   na  ambiguous  fp.region.size  fp.rate
0   indels         1625         2559  1363  1196  262    0     0  0.838769      0.820294      0.856039  0.838769    0.53263         0.513271         0.551915  0.0        0.0      2875001522    0.416
5  records         1625         2559  1363  1196  262    0     0  0.838769      0.820294      0.856039  0.838769    0.53263         0.513271         0.551915  0.0        0.0      2875001522    0.416
```
