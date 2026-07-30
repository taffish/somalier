#!/bin/sh
set -eu

src=$1
out=$2

mkdir -p "$out"
awk 'NR == 1 { print ">1"; next } { print }' \
  "$src/tests/test.fa" > "$out/test.fa"
install -m 0644 "$src/tests/test_sites.vcf" "$out/test_sites.vcf"
samtools faidx "$out/test.fa"

awk 'BEGIN { FS=OFS="\t" }
  /^##/ {
    print
    if ($0 ~ /^##fileformat=/) {
      print "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">"
    }
    next
  }
  /^#CHROM/ { print $0, "FORMAT", "test_sample"; next }
  {
    n++
    gt = (n == 49 ? "./." : "0/1")
    print $0, "GT", gt
  }' "$src/tests/test_sites.vcf" > "$out/gt_only.vcf"
bgzip -c "$out/gt_only.vcf" > "$out/gt_only.vcf.gz"
tabix -f -p vcf "$out/gt_only.vcf.gz"
rm -f "$out/gt_only.vcf"

awk 'BEGIN { FS=OFS="\t" }
  /^##/ {
    print
    if ($0 ~ /^##fileformat=/) {
      print "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">"
      print "##FORMAT=<ID=AD,Number=R,Type=Integer,Description=\"Allelic depths\">"
    }
    next
  }
  /^#CHROM/ {
    print $0, "FORMAT", "A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "Q1", "Q2"
    next
  }
  {
    n++
    if (n % 2 == 1) {
      a = "0/0:20,0"; b = "1/1:0,20"
    } else {
      a = "1/1:0,20"; b = "0/0:20,0"
    }
    print $0, "GT:AD", a, a, a, a, b, b, b, b, a, b
  }' "$src/tests/test_sites.vcf" > "$out/ancestry.vcf"
bgzip -c "$out/ancestry.vcf" > "$out/ancestry.vcf.gz"
tabix -f -p vcf "$out/ancestry.vcf.gz"
rm -f "$out/ancestry.vcf"

awk 'BEGIN { FS=OFS="\t" }
  /^#/ { print; next }
  { $8 = $8 ";AN=200000"; print }' \
  "$src/tests/test_sites.vcf" > "$out/population.vcf"

cat > "$out/ancestry-labels.tsv" <<'EOF'
A1	GroupA
A2	GroupA
A3	GroupA
A4	GroupA
B1	GroupB
B2	GroupB
B3	GroupB
B4	GroupB
EOF

cat > "$out/family.fam" <<'EOF'
FAM	father	0	0	1	1
FAM	mother	0	0	2	1
FAM	child	father	mother	1	1
EOF

chrom=$(awk '!/^#/ { print $1; exit }' "$out/test_sites.vcf")
pos=$(awk '!/^#/ { print $2; exit }' "$out/test_sites.vcf")
length=$(awk -v c="$chrom" '$1 == c { print $2; exit }' "$out/test.fa.fai")
start=$((pos - 24))
stop=$((start + 49))
sequence=$(samtools faidx "$out/test.fa" "$chrom:$start-$stop" | awk 'NR > 1 { printf "%s", $0 }')
qual=IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
{
  printf '@HD\tVN:1.6\tSO:coordinate\n'
  printf '@SQ\tSN:%s\tLN:%s\n' "$chrom" "$length"
  printf '@RG\tID:rg1\tSM:bam_sample\n'
  i=1
  while [ "$i" -le 10 ]; do
    printf 'read%s\t0\t%s\t%s\t60\t50M\t*\t0\t0\t%s\t%s\tRG:Z:rg1\n' \
      "$i" "$chrom" "$start" "$sequence" "$qual"
    i=$((i + 1))
  done
} > "$out/test.sam"
samtools view -b -o "$out/test.unsorted.bam" "$out/test.sam"
samtools sort -o "$out/test.bam" "$out/test.unsorted.bam"
samtools index "$out/test.bam"
samtools view -C -T "$out/test.fa" -o "$out/test.cram" "$out/test.bam"
samtools index "$out/test.cram"
rm -f "$out/test.sam" "$out/test.unsorted.bam"
samtools quickcheck "$out/test.bam" "$out/test.cram"
test "$(samtools view -c "$out/test.bam")" -eq 10
