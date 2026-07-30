#!/bin/sh
set -eu

mode=${1:-all}
data=/opt/somalier/share/testdata
tmp=${TMPDIR:-/tmp}/taf-somalier-${mode}-$$

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$tmp"

identity() {
  output=$(somalier --help 2>&1)
  printf '%s\n' "$output" | grep -Fx 'somalier version: 0.3.3' >/dev/null
  for command in extract relate ancestry AB_plot contamination find-sites pedrel; do
    printf '%s\n' "$output" | grep -F "  $command" >/dev/null
    somalier "$command" --help >"$tmp/$command.help" 2>&1
    test -s "$tmp/$command.help"
  done
  grep -F 'upstream_commit=210980f31c27546e064c8af253deafed4fb5af43' \
    /opt/somalier/share/doc/somalier/source.txt >/dev/null
  grep -F 'dependency_lock_sha256=' \
    /opt/somalier/share/doc/somalier/source.txt >/dev/null
  test -s /opt/somalier/share/licenses/somalier/LICENSE
  test -s /opt/somalier/share/ancestry-labels-1kg.tsv
}

extract_vcf() {
  mkdir -p "$tmp/sketches"
  somalier extract \
    --sites "$data/test_sites.vcf" \
    --fasta "$data/test.fa" \
    --out-dir "$tmp/sketches" \
    "$data/gt_only.vcf.gz" >"$tmp/extract.log" 2>&1
  test -s "$tmp/sketches/test_sample.somalier"
  grep -F '[somalier] found 49 sites' "$tmp/extract.log" >/dev/null
}

extract_bam() {
  mkdir -p "$tmp/sketches"
  somalier extract \
    --sites "$data/test_sites.vcf" \
    --fasta "$data/test.fa" \
    --out-dir "$tmp/sketches" \
    "$data/test.bam" >"$tmp/extract.log" 2>&1
  test -s "$tmp/sketches/bam_sample.somalier"
}

extract_cram() {
  mkdir -p "$tmp/sketches"
  somalier extract \
    --sites "$data/test_sites.vcf" \
    --fasta "$data/test.fa" \
    --out-dir "$tmp/sketches" \
    "$data/test.cram" >"$tmp/extract.log" 2>&1
  test -s "$tmp/sketches/bam_sample.somalier"
}

make_pair() {
  mkdir -p "$tmp/A" "$tmp/B"
  somalier extract --sample-prefix A- \
    --sites "$data/test_sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/A" "$data/gt_only.vcf.gz" >/dev/null 2>&1
  somalier extract --sample-prefix B- \
    --sites "$data/test_sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/B" "$data/gt_only.vcf.gz" >/dev/null 2>&1
}

relate() {
  make_pair
  printf '%s\n%s\n' \
    "$tmp/A/test_sample.somalier" \
    "$tmp/B/test_sample.somalier" > "$tmp/sketches.list"
  somalier relate --sites "$data/test_sites.vcf" \
    --output-prefix "$tmp/related" "$tmp/sketches.list" \
    >"$tmp/relate.log" 2>&1
  test -s "$tmp/related.samples.tsv"
  test -s "$tmp/related.pairs.tsv"
  test -s "$tmp/related.groups.tsv"
  test -s "$tmp/related.html"
  grep -F 'A-test_sample' "$tmp/related.samples.tsv" >/dev/null
  grep -F 'B-test_sample' "$tmp/related.samples.tsv" >/dev/null
  grep -F 'contamination_charr' "$tmp/related.samples.tsv" >/dev/null
  grep -F 'Plotly.newPlot' "$tmp/related.html" >/dev/null
}

ab_plot() {
  extract_vcf
  somalier AB_plot --sites "$data/test_sites.vcf" \
    --output "$tmp/ab.html" "$tmp/sketches/test_sample.somalier" \
    >"$tmp/ab.log" 2>&1
  test -s "$tmp/ab.html"
  grep -F 'Plotly.newPlot' "$tmp/ab.html" >/dev/null
  grep -F 'test_sample AB' "$tmp/ab.html" >/dev/null
}

contamination() {
  make_pair
  somalier contamination --sites "$data/test_sites.vcf" \
    --output "$tmp/contam" \
    "$tmp/A/test_sample.somalier" "$tmp/B/test_sample.somalier" \
    >"$tmp/contamination.log" 2>&1
  test -s "$tmp/contam.samples.tsv"
  test -s "$tmp/contam.pairs.tsv"
  awk -F '\t' 'NR == 1 && $1 == "#sample_name" && \
    $3 == "contamination_charr" { ok=1 } END { exit !ok }' \
    "$tmp/contam.samples.tsv"
  awk -F '\t' 'NR == 1 && $1 == "#sample_name" && \
    $2 == "anchor_sample" && $4 == "contamination_mle" \
    { ok=1 } END { exit !ok }' "$tmp/contam.pairs.tsv"
}

find_sites() {
  somalier find-sites --min-AN 1 --min-AF 0.1 --snp-dist 1 \
    --output-vcf "$tmp/sites.vcf.gz" "$data/population.vcf" \
    >"$tmp/find-sites.log" 2>&1
  test -s "$tmp/sites.vcf.gz"
  gzip -t "$tmp/sites.vcf.gz"
  gzip -cd "$tmp/sites.vcf.gz" | grep -v '^#' | grep -F 'AF=' >/dev/null
}

pedrel() {
  somalier pedrel --min-relatedness 0.1 --output "$tmp/pedrel.tsv" \
    "$data/family.fam" >"$tmp/pedrel.log" 2>&1
  test -s "$tmp/pedrel.tsv"
  awk -F '\t' 'NR == 1 && $1 == "sample_a" && $2 == "sample_b" && \
    $3 == "relatedness" { ok=1 } END { exit !ok }' "$tmp/pedrel.tsv"
  grep -F 'child' "$tmp/pedrel.tsv" >/dev/null
  grep -F 'father' "$tmp/pedrel.tsv" >/dev/null
}

ancestry() {
  mkdir -p "$tmp/sketches"
  somalier extract --sites "$data/test_sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/sketches" "$data/ancestry.vcf.gz" \
    >"$tmp/extract.log" 2>&1
  OPENBLAS_NUM_THREADS=1 somalier ancestry \
    --labels "$data/ancestry-labels.tsv" \
    --n-pcs 1 --nn-hidden-size 4 --nn-batch-size 2 --nn-test-samples 2 \
    --output-prefix "$tmp/ancestry" \
    "$tmp/sketches/A1.somalier" "$tmp/sketches/A2.somalier" \
    "$tmp/sketches/A3.somalier" "$tmp/sketches/A4.somalier" \
    "$tmp/sketches/B1.somalier" "$tmp/sketches/B2.somalier" \
    "$tmp/sketches/B3.somalier" "$tmp/sketches/B4.somalier" \
    ++ "$tmp/sketches/Q1.somalier" "$tmp/sketches/Q2.somalier" \
    >"$tmp/ancestry.log" 2>&1
  test -s "$tmp/ancestry.somalier-ancestry.tsv"
  test -s "$tmp/ancestry.somalier-ancestry.html"
  grep -F '#sample_id' "$tmp/ancestry.somalier-ancestry.tsv" >/dev/null
  grep -F 'Q1' "$tmp/ancestry.somalier-ancestry.tsv" >/dev/null
  grep -F 'Plotly.newPlot' "$tmp/ancestry.somalier-ancestry.html" >/dev/null
}

run_mode() {
  case "$1" in
    identity) identity ;;
    extract-vcf) extract_vcf ;;
    extract-bam) extract_bam ;;
    extract-cram) extract_cram ;;
    relate) relate ;;
    ab-plot) ab_plot ;;
    contamination) contamination ;;
    find-sites) find_sites ;;
    pedrel) pedrel ;;
    ancestry) ancestry ;;
    *) echo "unknown smoke mode: $1" >&2; exit 2 ;;
  esac
}

if [ "$mode" = all ]; then
  for item in identity extract-vcf extract-bam extract-cram relate ab-plot \
    contamination find-sites pedrel ancestry; do
    "$0" "$item"
  done
else
  run_mode "$mode"
fi
