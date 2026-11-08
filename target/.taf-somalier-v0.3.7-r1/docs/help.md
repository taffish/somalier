somalier 0.3.7-r1

Purpose:
  Genome sketches for sample identity, relatedness and ancestry/contamination QC.

Usage:
  taf-somalier -- --help
  taf-somalier somalier COMMAND --help

Common tasks:
  taf-somalier somalier extract --sites sites.vcf.gz --fasta reference.fa \
    --out-dir sketches sample.bam
  taf-somalier somalier relate --sites sites.vcf.gz --ped cohort.fam \
    --output-prefix cohort sketches/*.somalier
  taf-somalier somalier contamination --sites sites.vcf.gz \
    --output contamination sketches/*.somalier
  taf-somalier somalier AB_plot --sites sites.vcf.gz \
    --output ab.html sketches/*.somalier

Required inputs:
  Indexed BAM/CRAM or compressed VCF/BCF; matching FASTA + .fai and ordered sites.
  Supply authorized sites matching your assembly and chr naming; see the README.
    taf-somalier somalier find-sites --AN-field COHORT_AN --AF-field COHORT_AF \
      --output-vcf selected.vcf.gz population.vcf.gz
  Output site records use standard INFO/AN and INFO/AF. Set --min-AN and
  --min-AF for your population; pedrel takes a PED/FAM file.

Shared ancestry setup (explicit download, about 0.7 GB free space):
  root="$HOME/.local/share/taffish/resources/somalier"
  mkdir -p "$root"
  export TAFFISH_SOMALIER_RESOURCE_INSTALL_ROOT="$root"
  Docker:
    TAFFISH_CONTAINER_BACKEND=docker taf-somalier somalier-resources install \
      --resource 1kg-3479773 --resource-root /resource-install
  Podman:
    TAFFISH_CONTAINER_BACKEND=podman taf-somalier somalier-resources install \
      --resource 1kg-3479773 --resource-root /resource-install
  Apptainer (native Linux):
    TAFFISH_CONTAINER_BACKEND=apptainer taf-somalier somalier-resources install \
      --resource 1kg-3479773 --resource-root /resource-install
  unset TAFFISH_SOMALIER_RESOURCE_INSTALL_ROOT
  Add --dry-run to preview. Administrators can install once in the same
  /usr/local/share/taffish/resources/somalier parent (or the resources/somalier
  directory under TAFFISH_SYSTEM_HOME); users select the ID read-only.

Use a prepared reference:
  export TAFFISH_SOMALIER_RESOURCE_ID=1kg-3479773
  taf-somalier somalier ancestry \
    --labels /opt/somalier/share/ancestry-labels-1kg.tsv --output-prefix ancestry \
    '/somalier-resource/1kg-somalier/*.somalier' ++ query-sketches/*.somalier
  Override: TAFFISH_SOMALIER_RESOURCE_PATH=/safe/prepared/root (host Python 3 needed)
  Without host Python 3, use the manual-bind commands below.

Manual bind: export TAFFISH_SOMALIER_RESOURCE_AUTO_MOUNT=0; verify before use.
  Docker: TAFFISH_DOCKER_RUN_ARGS="-v /safe/root:/somalier-resource:ro"
  Podman: TAFFISH_PODMAN_RUN_ARGS="-v /safe/root:/somalier-resource:ro"
  Apptainer: TAFFISH_APPTAINER_RUN_ARGS="--bind /safe/root:/somalier-resource:ro"
  Export the appropriate variable, then run the same wrapper command.
  Physical resource paths must use letters, digits, _, ., /, + or -.
  Invalid library? Check the selected ID/path; do not overwrite it.
  Local sites import: taf-somalier somalier-resources install --help
  Verify: taf-somalier somalier-resources verify /somalier-resource

Key outputs:
  SAMPLE.somalier; PREFIX.samples.tsv / pairs.tsv / groups.tsv / html.
  Ancestry: PREFIX.somalier-ancestry.tsv and .html; AB_plot: requested HTML.
  Open HTML directly in your host browser for all three backends; no port setup.
  Use a fresh output prefix/directory: existing files can be overwritten.

Immediate notes:
  relate needs matching --sites for correct REF/ALT homozygous counts in TSV/HTML.
  Without --sites, counts remain alphabetical A/B; INFO/AF is required for CHARR.
  Keep ordered sites consistent; RNA sites are not the standard genomic panel.
  Ancestry references precede ++; query sketches follow. Predictions are
  experimental, not clinical validation. Protect sample names in HTML/TSVs.
  Repeatable pair subset: taf-somalier env SOMALIER_SEED=42 somalier relate ...
  Space-containing values need literal inner quotes, e.g.
    --out-dir '"output with spaces"' or --license-note '"Your actual permission"'.

More help:
  taf-somalier somalier COMMAND --help
  https://github.com/taffish/somalier

Wrapper options:
  taf-somalier --help       Show this task help.
  taf-somalier --version    Show wrapper identity; upstream identity is in --help.
  taf-somalier --compile    Print the generated wrapper shell.
