#!/bin/sh
set -eu

mode=${1:-all}
stage=$mode
data=/opt/somalier/share/testdata
tmp=$(mktemp -d "${TMPDIR:-/tmp}/taf-somalier.XXXXXXXX")

cleanup() {
  status=$?
  trap - EXIT
  set +e
  if [ "$status" -ne 0 ]; then
    printf 'smoke-stage=%s exit=%s\n' "$stage" "$status" >&2
    for log in "$tmp"/*.log; do
      [ -f "$log" ] || continue
      printf 'log=%s\n' "${log##*/}" >&2
      tail -n 80 "$log" >&2
    done
  fi
  rm -rf "$tmp"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

identity() {
  stage=identity-main-help
  somalier --help >"$tmp/identity.log" 2>&1
  output=$(cat "$tmp/identity.log")
  printf '%s\n' "$output" | grep -Fx 'somalier version: 0.3.4' >/dev/null
  for command in extract relate ancestry AB_plot contamination find-sites pedrel; do
    stage="identity-$command-help"
    printf '%s\n' "$output" | grep -F "  $command" >/dev/null
    somalier "$command" --help >"$tmp/$command-help.log" 2>&1
    test -s "$tmp/$command-help.log"
  done
  stage=identity-provenance
  grep -F 'upstream_commit=ff58fdade8f4f8293d904f10e0a4a13f1fac808d' \
    /opt/somalier/share/doc/somalier/source.txt >/dev/null
  grep -F 'dependency_lock_sha256=' \
    /opt/somalier/share/doc/somalier/source.txt >/dev/null
  test -s /opt/somalier/share/licenses/somalier/LICENSE
  python3 /opt/somalier/share/testdata/check-notices.py
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
    --out-dir "$tmp/A" "$data/gt_only.vcf.gz" >"$tmp/extract-A.log" 2>&1
  somalier extract --sample-prefix B- \
    --sites "$data/test_sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/B" "$data/gt_only.vcf.gz" >"$tmp/extract-B.log" 2>&1
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
  offline_html "$tmp/related.html"
}

ab_plot() {
  extract_vcf
  somalier AB_plot --sites "$data/test_sites.vcf" \
    --output "$tmp/ab.html" "$tmp/sketches/test_sample.somalier" \
    >"$tmp/ab.log" 2>&1
  test -s "$tmp/ab.html"
  grep -F 'Plotly.newPlot' "$tmp/ab.html" >/dev/null
  grep -F 'test_sample AB' "$tmp/ab.html" >/dev/null
  offline_html "$tmp/ab.html"
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
  offline_html "$tmp/ancestry.somalier-ancestry.html"
}

offline_html() {
  grep -F 'data-taffish-asset="plotly-' "$1" >/dev/null
  grep -F 'data-taffish-license="LICENSE-plotly-' "$1" >/dev/null
  if grep -E '<(script|link)[^>]*(src|href)="https?://' "$1"; then
    echo 'unexpected external HTML runtime dependency' >&2
    exit 1
  fi
}

resources() {
  somalier-resources --help >"$tmp/resources-help.log" 2>&1
  somalier-resources list >"$tmp/catalog.log" 2>&1
  grep -F '1kg-3479773' "$tmp/catalog.log" >/dev/null
  somalier-resources install --resource 1kg-3479773 --resource-root "$tmp/install" \
    --dry-run >"$tmp/dry-run.log" 2>&1
  test ! -e "$tmp/install"
  sha=$(sha256sum "$data/test_sites.vcf" | awk '{print $1}')
  for attempt in 1 2; do
    somalier-resources install --resource local-tiny --resource-root "$tmp/install" \
      --source "$data/test_sites.vcf" --sha256 "$sha" --license-note 'MIT upstream tiny fixture' \
      >"$tmp/install-$attempt.log" 2>&1
  done
  grep -F 'already installed; no writes or download' "$tmp/install-2.log" >/dev/null
  somalier-resources verify "$tmp/install/local-tiny" >"$tmp/verify.log" 2>&1
  mkdir "$tmp/shared-sketches"
  somalier extract --sites "$tmp/install/local-tiny/sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/shared-sketches" "$data/gt_only.vcf.gz" >"$tmp/shared-extract.log" 2>&1
  test -s "$tmp/shared-sketches/test_sample.somalier"
  printf '\ncorrupt\n' >> "$tmp/install/local-tiny/sites.vcf"
  if somalier-resources verify "$tmp/install/local-tiny" >"$tmp/corrupt.log" 2>&1; then exit 1; fi
  grep -F 'checksum mismatch' "$tmp/corrupt.log" >/dev/null
  if somalier-resources install --resource unknown --resource-root "$tmp/no" \
      >"$tmp/unknown.log" 2>&1; then exit 1; fi
  test ! -e "$tmp/no"
  echo 'resources=install-idempotent-verify-extract-corrupt-reject PASS'
}

reference_error() {
  awk 'BEGIN {FS=OFS="\t"} /^#/ {print; next} !changed {$4=$5; changed=1} {print}' \
    "$data/test_sites.vcf" > "$tmp/bad-sites.vcf"
  locus=$(awk '!/^#/ {print $1 ":" $2; exit}' "$data/test_sites.vcf")
  mkdir "$tmp/sketches"
  if somalier extract --sites "$tmp/bad-sites.vcf" --fasta "$data/test.fa" \
    --out-dir "$tmp/sketches" "$data/test.bam" >"$tmp/reference-error.log" 2>&1; then exit 1; fi
  grep -F "$locus" "$tmp/reference-error.log" >/dev/null
}

cigar_boundary() {
  for encoding in m eqx; do
    mkdir "$tmp/$encoding"
    somalier extract --sites "$data/test_sites.vcf" --fasta "$data/test.fa" \
      --out-dir "$tmp/$encoding" "$data/boundary-$encoding.bam" \
      >"$tmp/boundary-$encoding.log" 2>&1
    test -s "$tmp/$encoding/boundary.somalier"
  done
  cmp "$tmp/m/boundary.somalier" "$tmp/eqx/boundary.somalier"
  echo 'CIGAR-boundary=M-equals-EQX PASS'
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
    cigar-boundary) cigar_boundary ;;
    resources) resources ;;
    reference-error) reference_error ;;
    *) echo "unknown smoke mode: $1" >&2; exit 2 ;;
  esac
}

if [ "$mode" = all ]; then
  for item in identity extract-vcf extract-bam extract-cram relate ab-plot \
    contamination find-sites pedrel ancestry cigar-boundary resources reference-error; do
    "$0" "$item"
  done
else
  run_mode "$mode"
fi
