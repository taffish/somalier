somalier 0.3.4-r1

Purpose:
  Genome sketches for sample identity, relatedness and ancestry/contamination QC.
  CLI calculations produce TSVs and offline HTML viewed in your host browser.

Usage:
  taf-somalier -- --help
  taf-somalier somalier COMMAND --help

Common tasks:
  taf-somalier somalier extract --sites sites.vcf.gz --fasta reference.fa \
    --out-dir sketches sample.bam
  taf-somalier somalier relate --sites sites.vcf.gz --ped cohort.fam \
    --output-prefix cohort sketches/*.somalier
  taf-somalier somalier relate --output-prefix cohort sketches.list
  taf-somalier somalier contamination --sites sites.vcf.gz \
    --output contamination sketches/*.somalier
  taf-somalier somalier AB_plot --sites sites.vcf.gz \
    --output ab.html sketches/*.somalier

Required inputs:
  Indexed BAM/CRAM or compressed VCF/BCF; matching FASTA + .fai and ordered sites.
  Prefer BAM/CRAM or joint calls over single-sample VCF/GVCF.
  No production references are bundled. Choose assembly/chr naming explicitly.
  Obtain authorized sites yourself; official links/checksums are in the README.
  find-sites selects sites from your population VCF; pedrel accepts PED/FAM.

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
  /usr/local/share/taffish/resources/somalier parent; users reuse read-only.

Use a prepared reference:
  export TAFFISH_SOMALIER_RESOURCE_ID=1kg-3479773
  taf-somalier somalier ancestry \
    --labels /opt/somalier/share/ancestry-labels-1kg.tsv --output-prefix ancestry \
    '/somalier-resource/1kg-somalier/*.somalier' ++ query-sketches/*.somalier
  Select Docker, Podman or Apptainer using TAFFISH_CONTAINER_BACKEND.
  Override: TAFFISH_SOMALIER_RESOURCE_PATH=/safe/prepared/root
  Disable discovery: TAFFISH_SOMALIER_RESOURCE_AUTO_MOUNT=0
  Native amd64/arm64 images; Apptainer requires Linux, not macOS.

Manual resource bind (disable automatic mounting first):
  Docker: TAFFISH_DOCKER_RUN_ARGS="-v /safe/root:/somalier-resource:ro"
  Podman: TAFFISH_PODMAN_RUN_ARGS="-v /safe/root:/somalier-resource:ro"
  Apptainer: TAFFISH_APPTAINER_RUN_ARGS="--bind /safe/root:/somalier-resource:ro"
  Export the appropriate variable, then run the same wrapper command.
  Physical resource paths must use letters, digits, _, ., /, + or -.
  Local sites import: taf-somalier somalier-resources install --help
  Verify: taf-somalier somalier-resources verify /somalier-resource

Key outputs:
  SAMPLE.somalier; PREFIX.samples.tsv / pairs.tsv / groups.tsv / html.
  Ancestry: PREFIX.somalier-ancestry.tsv and .html; AB_plot: requested HTML.
  Open HTML directly in your host browser for all three backends; no port setup.
  Use a fresh output prefix/directory: existing files can be overwritten.

Immediate notes:
  Keep ordered sites consistent; RNA sites are not the standard genomic panel.
  Reference/input indexes must be prepared before read-only analysis.
  Ancestry references precede ++; query sketches follow. Predictions are
  experimental, not clinical validation. Protect sample names in HTML/TSVs.
  To limit ancestry CPU BLAS: taf-somalier env OPENBLAS_NUM_THREADS=1 somalier ...
  Use "taf-somalier somalier COMMAND", not a bare subcommand.
  Space-containing values need literal inner quotes, e.g.
    --out-dir '"output with spaces"' or --license-note '"Your actual permission"'.

More help:
  taf-somalier somalier COMMAND --help
  https://github.com/taffish/somalier

Wrapper options:
  taf-somalier --help       Show this task help.
  taf-somalier --version    Show wrapper identity; upstream identity is in --help.
  taf-somalier --compile    Print the generated wrapper shell.
